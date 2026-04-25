import csv
import json
import time
from datetime import datetime, time as dt_time, timedelta
from typing import Dict, Optional

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.db.models.functions import TruncDate, TruncHour
from django.http import HttpRequest, HttpResponse, JsonResponse, StreamingHttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods

from django_ip_safeguard.conf import get_settings
from django_ip_safeguard.models import IpAccessLog, IpBanRecord, IpGuardPolicy
from django_ip_safeguard.services.cache import RedisCacheService
from django_ip_safeguard.services.policy_service import invalidate_policy_cache


def _load_json_body(request: HttpRequest) -> dict:
    raw = request.body.decode("utf-8").strip()
    if not raw:
        return {}
    return json.loads(raw)


def api_success(data=None, message: str = "ok", code: int = 0, status: int = 200) -> JsonResponse:
    return JsonResponse({"code": code, "message": message, "data": data or {}}, status=status)


def api_error(message: str, code: int = 4000, status: int = 400, data=None) -> JsonResponse:
    return JsonResponse({"code": code, "message": message, "data": data or {}}, status=status)


def _get_int_param(request: HttpRequest, name: str, default: int, min_value: int = 1, max_value: int = 200) -> int:
    try:
        value = int(request.GET.get(name, default))
    except (TypeError, ValueError):
        return default
    return max(min_value, min(max_value, value))


def _apply_access_log_filters(request: HttpRequest, queryset):
    """审计日志列表与导出共用的筛选条件。"""

    decision = str(request.GET.get("decision", "")).strip()
    country = str(request.GET.get("country", "")).strip().upper()
    q = str(request.GET.get("q", "")).strip()
    path_q = str(request.GET.get("path", "")).strip()
    start_s = str(request.GET.get("start", "")).strip()
    end_s = str(request.GET.get("end", "")).strip()
    if decision in {"allow", "block"}:
        queryset = queryset.filter(decision=decision)
    if country:
        queryset = queryset.filter(country_code=country)
    if q:
        queryset = queryset.filter(ip__icontains=q)
    if path_q:
        queryset = queryset.filter(path__icontains=path_q)
    if start_s:
        d = parse_date(start_s)
        if d:
            start_dt = timezone.make_aware(datetime.combine(d, dt_time.min))
            queryset = queryset.filter(created_at__gte=start_dt)
    if end_s:
        d = parse_date(end_s)
        if d:
            end_dt = timezone.make_aware(datetime.combine(d, dt_time.max))
            queryset = queryset.filter(created_at__lte=end_dt)
    return queryset


def _access_log_to_dict(item: IpAccessLog) -> dict:
    """单条访问审计序列化（列表与近期接口复用）。"""

    return {
        "ip": item.ip,
        "country_code": item.country_code,
        "risk_score": item.risk_score,
        "risk_tags": item.risk_tags,
        "decision": item.decision,
        "reason": item.reason,
        "path": item.path,
        "created_at": item.created_at.isoformat(),
    }


def _ban_record_to_dict(item: IpBanRecord) -> dict:
    """单条封禁记录序列化。"""

    return {
        "ip": item.ip,
        "ban_reason": item.ban_reason,
        "ban_source": item.ban_source,
        "expired_at": item.expired_at.isoformat() if item.expired_at else None,
        "is_active": item.is_active,
        "created_at": item.created_at.isoformat(),
    }


def _get_days_param(request: HttpRequest, default: int = 7, max_days: int = 30) -> int:
    """查询参数 days，表示回溯自然日数。"""

    try:
        days = int(request.GET.get("days", default))
    except (TypeError, ValueError):
        days = default
    return max(1, min(max_days, days))


@staff_member_required
@require_GET
def dashboard_page_view(request: HttpRequest) -> HttpResponse:
    """Dashboard 页面（企业版管理入口）。"""

    html = """
    <html>
      <head><title>IP Guard Dashboard</title></head>
      <body>
        <h1>IP Guard 企业运营面板</h1>
        <p>请通过以下接口查看数据：</p>
        <ul>
          <li>/api/dashboard/ - 统计指标</li>
          <li>/api/recent-records/ - 近几日攻击与访问汇总</li>
          <li>/api/policy/ - 策略读取/更新</li>
          <li>/api/unban/ - 解封 IP（POST）</li>
          <li>/api/health/ - 健康状态</li>
        </ul>
      </body>
    </html>
    """
    return HttpResponse(html)


@staff_member_required
@require_GET
def dashboard_api_view(request: HttpRequest) -> JsonResponse:
    """运营统计接口。"""

    since = timezone.now() - timedelta(days=1)
    today_logs = IpAccessLog.objects.filter(created_at__gte=since)
    blocked_count = today_logs.filter(decision="block").count()
    allow_count = today_logs.filter(decision="allow").count()
    total_count = today_logs.count()
    top_risk_ips = list(
        today_logs.filter(decision="block")
        .values("ip")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    country_distribution = list(
        today_logs.values("country_code").annotate(count=Count("id")).order_by("-count")[:10]
    )
    decision_rows = today_logs.values("decision").annotate(c=Count("id"))
    decision_distribution = {row["decision"]: row["c"] for row in decision_rows}
    block_rate = round(blocked_count / total_count, 4) if total_count else 0.0
    top_paths = list(
        today_logs.values("path").annotate(count=Count("id")).order_by("-count")[:10]
    )
    top_block_reasons = list(
        today_logs.filter(decision="block")
        .values("reason")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    hourly_trend = list(
        today_logs.annotate(bucket=TruncHour("created_at"))
        .values("bucket")
        .annotate(total=Count("id"), blocked=Count("id", filter=Q(decision="block")))
        .order_by("bucket")
    )
    for row in hourly_trend:
        b = row.get("bucket")
        if b is not None:
            row["bucket"] = b.isoformat()

    return api_success(
        {
            "total_count_24h": total_count,
            "block_count_24h": blocked_count,
            "allow_count_24h": allow_count,
            "block_rate_24h": block_rate,
            "decision_distribution": decision_distribution,
            "top_risk_ips": top_risk_ips,
            "country_distribution": country_distribution,
            "top_paths": top_paths,
            "top_block_reasons": top_block_reasons,
            "hourly_trend": hourly_trend,
        }
    )


@staff_member_required
@require_http_methods(["GET", "POST"])
def policy_view(request: HttpRequest) -> JsonResponse:
    """策略中心读取与更新接口。"""

    policy, _created = IpGuardPolicy.objects.get_or_create(name="default")
    if request.method == "GET":
        return api_success(
            {
                "name": policy.name,
                "enabled": policy.enabled,
                "risk_score_threshold": policy.risk_score_threshold,
                "blocked_risk_tags": policy.blocked_risk_tags,
                "allowed_countries": policy.allowed_countries,
                "blocked_countries": policy.blocked_countries,
                "ip_whitelist": policy.ip_whitelist,
                "fail_open": policy.fail_open,
                "fail_open_path_prefixes": policy.fail_open_path_prefixes,
                "fail_close_path_prefixes": policy.fail_close_path_prefixes,
                "block_status_code": policy.block_status_code,
                "cache_ttl": policy.cache_ttl,
                "ban_ttl": policy.ban_ttl,
                "use_db_log": policy.use_db_log,
                "updated_at": policy.updated_at.isoformat(),
            }
        )

    try:
        payload = _load_json_body(request)
    except json.JSONDecodeError:
        return api_error("JSON 格式错误", code=4001, status=400)
    list_json_fields = {
        "blocked_risk_tags",
        "allowed_countries",
        "blocked_countries",
        "ip_whitelist",
        "fail_open_path_prefixes",
        "fail_close_path_prefixes",
    }
    editable_fields = [
        "enabled",
        "risk_score_threshold",
        "blocked_risk_tags",
        "allowed_countries",
        "blocked_countries",
        "ip_whitelist",
        "fail_open",
        "fail_open_path_prefixes",
        "fail_close_path_prefixes",
        "block_status_code",
        "cache_ttl",
        "ban_ttl",
        "use_db_log",
    ]
    for field in editable_fields:
        if field not in payload:
            continue
        val = payload[field]
        if field in list_json_fields and not isinstance(val, list):
            return api_error(f"字段 {field} 必须为 JSON 数组", code=4005, status=400)
        setattr(policy, field, val)
    policy.save()
    invalidate_policy_cache()
    return api_success({"name": policy.name}, message="策略已更新")


@staff_member_required
@require_http_methods(["POST"])
def unban_ip_view(request: HttpRequest) -> JsonResponse:
    """手动解封 IP。"""

    try:
        payload = _load_json_body(request)
    except json.JSONDecodeError:
        return api_error("JSON 格式错误", code=4001, status=400)
    ip = str(payload.get("ip", "")).strip()
    if not ip:
        return api_error("ip 参数不能为空", code=4002, status=400)

    cfg = get_settings()
    cache_service = RedisCacheService(cfg.redis_url)
    cache_service.unban(ip)
    IpBanRecord.objects.filter(ip=ip).update(is_active=False, expired_at=timezone.now())
    return api_success({"ip": ip}, message="解封成功")


@staff_member_required
@require_http_methods(["POST"])
def ban_ip_view(request: HttpRequest) -> JsonResponse:
    """手动封禁 IP。"""

    try:
        payload = _load_json_body(request)
    except json.JSONDecodeError:
        return api_error("JSON 格式错误", code=4001, status=400)

    ip = str(payload.get("ip", "")).strip()
    reason = str(payload.get("reason", "manual_ban")).strip()[:255]
    ttl = int(payload.get("ttl", 86400))
    if not ip:
        return api_error("ip 参数不能为空", code=4002, status=400)

    cfg = get_settings()
    cache_service = RedisCacheService(cfg.redis_url)
    cache_service.set_ban(ip=ip, reason=reason, ttl=max(60, ttl))
    expire_at = timezone.now() + timedelta(seconds=max(60, ttl))
    IpBanRecord.objects.update_or_create(
        ip=ip,
        defaults={
            "ban_reason": reason,
            "ban_source": "manual",
            "expired_at": expire_at,
            "is_active": True,
        },
    )
    return api_success({"ip": ip, "ttl": max(60, ttl)}, message="封禁成功")


@staff_member_required
@require_GET
def ban_list_view(request: HttpRequest) -> JsonResponse:
    """封禁列表分页查询。"""

    page = _get_int_param(request, "page", 1)
    page_size = _get_int_param(request, "page_size", 20)
    active = request.GET.get("active")
    q = str(request.GET.get("q", "")).strip()
    source = str(request.GET.get("source", "")).strip()
    queryset = IpBanRecord.objects.all().order_by("-created_at")
    if active in {"true", "false"}:
        queryset = queryset.filter(is_active=(active == "true"))
    if q:
        queryset = queryset.filter(ip__icontains=q)
    if source:
        queryset = queryset.filter(ban_source=source)
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    items = [_ban_record_to_dict(item) for item in page_obj.object_list]
    return api_success(
        {
            "items": items,
            "pagination": {
                "page": page_obj.number,
                "page_size": page_size,
                "total": paginator.count,
                "num_pages": paginator.num_pages,
            },
        }
    )


@staff_member_required
@require_GET
def access_log_list_view(request: HttpRequest) -> JsonResponse:
    """审计日志分页与筛选。"""

    page = _get_int_param(request, "page", 1)
    page_size = _get_int_param(request, "page_size", 20)
    queryset = IpAccessLog.objects.all().order_by("-created_at")
    queryset = _apply_access_log_filters(request, queryset)

    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    items = [_access_log_to_dict(item) for item in page_obj.object_list]
    return api_success(
        {
            "items": items,
            "pagination": {
                "page": page_obj.number,
                "page_size": page_size,
                "total": paginator.count,
                "num_pages": paginator.num_pages,
            },
        }
    )


class _Echo:
    """流式 CSV 写入缓冲区。"""

    def write(self, value):
        return value


@staff_member_required
@require_GET
def access_log_export_view(request: HttpRequest) -> StreamingHttpResponse:
    """按当前筛选条件导出审计日志（CSV，最多 1 万条）。"""

    queryset = IpAccessLog.objects.all().order_by("-created_at")
    queryset = _apply_access_log_filters(request, queryset)[:10000]

    pseudo_buffer = _Echo()

    def rows():
        writer = csv.writer(pseudo_buffer)
        yield "\ufeff"
        yield writer.writerow(["ip", "country_code", "risk_score", "risk_tags", "decision", "reason", "path", "created_at"])
        for item in queryset:
            yield writer.writerow(
                [
                    item.ip,
                    item.country_code,
                    item.risk_score,
                    json.dumps(item.risk_tags or [], ensure_ascii=False),
                    item.decision,
                    item.reason,
                    item.path,
                    item.created_at.isoformat(),
                ]
            )

    response = StreamingHttpResponse(rows(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="ip_guard_access_logs.csv"'
    return response


@staff_member_required
@require_GET
def recent_records_view(request: HttpRequest) -> JsonResponse:
    """近若干天的攻击（拦截）记录、全量访问记录、按日汇总与近期封禁。"""

    days = _get_days_param(request, default=7, max_days=30)
    attack_limit = _get_int_param(request, "attack_limit", 100, 1, 200)
    access_limit = _get_int_param(request, "access_limit", 100, 1, 200)
    ban_limit = _get_int_param(request, "ban_limit", 40, 1, 100)

    since = timezone.now() - timedelta(days=days)
    logs = IpAccessLog.objects.filter(created_at__gte=since)

    def _count_by_date(qs, decision: Optional[str] = None) -> Dict[str, int]:
        q = qs
        if decision in {"allow", "block"}:
            q = q.filter(decision=decision)
        rows = q.annotate(d=TruncDate("created_at")).values("d").annotate(c=Count("id"))
        out: Dict[str, int] = {}
        for row in rows:
            d = row["d"]
            if d is None:
                continue
            out[d.isoformat()] = row["c"]
        return out

    block_by_date = _count_by_date(logs, "block")
    allow_by_date = _count_by_date(logs, "allow")
    all_dates = sorted(set(block_by_date.keys()) | set(allow_by_date.keys()))
    daily_breakdown = [
        {
            "date": d,
            "block": block_by_date.get(d, 0),
            "allow": allow_by_date.get(d, 0),
            "total": block_by_date.get(d, 0) + allow_by_date.get(d, 0),
        }
        for d in all_dates
    ]

    attack_qs = logs.filter(decision="block").order_by("-created_at")[:attack_limit]
    access_qs = logs.order_by("-created_at")[:access_limit]
    ban_window = IpBanRecord.objects.filter(created_at__gte=since)
    ban_qs = ban_window.order_by("-created_at")[:ban_limit]

    return api_success(
        {
            "days": days,
            "since": since.isoformat(),
            "summary": {
                "total_access": logs.count(),
                "total_blocks": logs.filter(decision="block").count(),
                "total_allows": logs.filter(decision="allow").count(),
                "total_ban_events": ban_window.count(),
            },
            "daily_breakdown": daily_breakdown,
            "recent_attacks": [_access_log_to_dict(x) for x in attack_qs],
            "recent_access": [_access_log_to_dict(x) for x in access_qs],
            "recent_bans": [_ban_record_to_dict(x) for x in ban_qs],
        }
    )


@staff_member_required
@require_GET
def health_view(request: HttpRequest) -> JsonResponse:
    """插件健康状态接口。"""

    cfg = get_settings()
    cache_service = RedisCacheService(cfg.redis_url)
    t0 = time.perf_counter()
    redis_ok = cache_service.ping()
    redis_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    provider_failures = cache_service.get_provider_failures()
    return api_success(
        {
            "service": "django-ip-safeguard",
            "redis_ok": redis_ok,
            "redis_latency_ms": redis_latency_ms,
            "provider": cfg.provider,
            "policy_center_enabled": cfg.enable_policy_center,
            "provider_circuit_failures": provider_failures,
        }
    )


@login_required
@require_GET
def auth_me_view(request: HttpRequest) -> JsonResponse:
    """返回当前登录态信息。"""

    user = request.user
    if not user.is_staff:
        return api_error("权限不足", code=4030, status=403)
    return api_success(
        {
            "username": user.username,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
        }
    )


@ensure_csrf_cookie
@require_GET
def csrf_view(_request: HttpRequest) -> JsonResponse:
    """下发 CSRF Cookie。"""

    return api_success({"csrf": "ok"})


@require_http_methods(["POST"])
def login_view(request: HttpRequest) -> JsonResponse:
    """后台登录接口，使用 Django Session。"""

    try:
        payload = _load_json_body(request)
    except json.JSONDecodeError:
        return api_error("JSON 格式错误", code=4001, status=400)

    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    if not username or not password:
        return api_error("用户名或密码不能为空", code=4003, status=400)
    user = authenticate(request, username=username, password=password)
    if not user:
        return api_error("用户名或密码错误", code=4004, status=401)
    if not user.is_staff:
        return api_error("该账号无后台权限", code=4030, status=403)
    login(request, user)
    return api_success({"username": user.username}, message="登录成功")


@login_required
@require_http_methods(["POST"])
def logout_view(request: HttpRequest) -> JsonResponse:
    logout(request)
    return api_success(message="已退出登录")
