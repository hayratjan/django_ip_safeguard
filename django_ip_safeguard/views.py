import csv
import ipaddress
import json
import time
from datetime import datetime, time as dt_time, timedelta
from functools import wraps
from typing import Dict, List, Optional, Tuple

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.db.models.functions import TruncDate, TruncHour
from django.http import HttpRequest, HttpResponse, JsonResponse, StreamingHttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods

from django_ip_safeguard.conf import get_settings
from django_ip_safeguard.models import IpAccessLog, IpBanRecord, IpGeoPoolStatus, IpGuardPolicy
from django_ip_safeguard.services.cache import RedisCacheService
from django_ip_safeguard.services.jwt_service import (
    get_user_from_access_token,
    issue_token_pair,
    refresh_access_token,
)
from django_ip_safeguard.services.geo_ip_pool_sync import sync_all_geo_pools
from django_ip_safeguard.services.policy_service import GEO_POOL_RULE_CHOICES, invalidate_policy_cache


MAX_JSON_BODY_SIZE = 1024 * 1024


def _load_json_body(request: HttpRequest) -> dict:
    content_length = int(request.META.get("CONTENT_LENGTH", 0) or 0)
    if content_length > MAX_JSON_BODY_SIZE:
        raise ValueError(_("请求体过大，最大允许 %(size)s 字节") % {"size": MAX_JSON_BODY_SIZE})
    raw = request.body.decode("utf-8").strip()
    if not raw:
        return {}
    return json.loads(raw)


def api_success(data=None, message: str = "ok", code: int = 0, status: int = 200) -> JsonResponse:
    return JsonResponse({"code": code, "message": message, "data": data or {}}, status=status)


def api_error(message: str, code: int = 4000, status: int = 400, data=None) -> JsonResponse:
    return JsonResponse({"code": code, "message": message, "data": data or {}}, status=status)


def api_permission_required(*permissions: str, any_perm: bool = False):

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request: HttpRequest, *args, **kwargs):
            user = _resolve_request_user(request)
            if not user.is_authenticated:
                return api_error(_("未登录或登录已过期"), code=4010, status=401)
            if not user.is_staff:
                return api_error(_("权限不足"), code=4030, status=403)
            if not permissions:
                return view_func(request, *args, **kwargs)
            if any_perm:
                ok = any(user.has_perm(p) for p in permissions)
            else:
                ok = user.has_perms(permissions)
            if not ok:
                return api_error(_("权限不足：缺少操作权限"), code=4031, status=403)
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


def _resolve_request_user(request: HttpRequest):
    if request.user.is_authenticated:
        return request.user
    auth = str(request.headers.get("Authorization", "")).strip()
    if not auth.startswith("Bearer "):
        return request.user
    token = auth[7:].strip()
    if not token:
        return request.user
    user = get_user_from_access_token(token)
    if user is not None:
        request.user = user
    return request.user


def _get_int_param(request: HttpRequest, name: str, default: int, min_value: int = 1, max_value: int = 200) -> int:
    try:
        value = int(request.GET.get(name, default))
    except (TypeError, ValueError):
        return default
    return max(min_value, min(max_value, value))


def _normalize_country_codes(values: list, field_name: str) -> Tuple[Optional[List[str]], Optional[JsonResponse]]:
    out: List[str] = []
    seen = set()
    for raw in values:
        code = str(raw).strip().upper()
        if not code:
            continue
        if len(code) != 2 or not code.isalpha():
            return None, api_error(_("字段 %(field)s 仅支持两位国家码（如 CN/US）") % {"field": field_name}, code=4007, status=400)
        if code not in seen:
            seen.add(code)
            out.append(code)
    return out, None


def _normalize_ip_rules(values: list, field_name: str) -> Tuple[Optional[List[str]], Optional[JsonResponse]]:
    out: List[str] = []
    seen = set()
    for raw in values:
        rule = str(raw).strip()
        if not rule:
            continue
        try:
            if "/" in rule:
                net = ipaddress.ip_network(rule, strict=False)
                normalized = str(net)
            else:
                addr = ipaddress.ip_address(rule)
                normalized = str(addr)
        except ValueError:
            return None, api_error(_("字段 %(field)s 存在非法 IP/CIDR: %(rule)s") % {"field": field_name, "rule": rule}, code=4008, status=400)
        if normalized not in seen:
            seen.add(normalized)
            out.append(normalized)
    return out, None


def _normalize_string_list(values: list) -> List[str]:
    out: List[str] = []
    seen = set()
    for raw in values:
        s = str(raw).strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _apply_access_log_filters(request: HttpRequest, queryset):
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
    return {
        "ip": item.ip,
        "ban_reason": item.ban_reason,
        "ban_source": item.ban_source,
        "expired_at": item.expired_at.isoformat() if item.expired_at else None,
        "is_active": item.is_active,
        "created_at": item.created_at.isoformat(),
    }


def _get_days_param(request: HttpRequest, default: int = 7, max_days: int = 30) -> int:
    try:
        days = int(request.GET.get("days", default))
    except (TypeError, ValueError):
        days = default
    return max(1, min(max_days, days))


@staff_member_required
@require_GET
def dashboard_page_view(request: HttpRequest) -> HttpResponse:
    html = """
    <html>
      <head><title>IP Guard Dashboard</title></head>
      <body>
        <h1>IP Guard %s</h1>
        <p>%s</p>
        <ul>
          <li>/api/dashboard/ - %s</li>
          <li>/api/recent-records/ - %s</li>
          <li>/api/policy/ - %s</li>
          <li>/api/geo-pools/status/ - %s</li>
          <li>/api/geo-pools/sync/ - %s</li>
          <li>/api/unban/ - %s</li>
          <li>/api/health/ - %s</li>
        </ul>
      </body>
    </html>
    """ % (
        _("企业运营面板"),
        _("请通过以下接口查看数据："),
        _("统计指标"),
        _("近几日攻击与访问汇总"),
        _("策略读取/更新"),
        _("中国内/国际 CIDR 池同步状态"),
        _("手动同步 CIDR 池至 Redis"),
        _("解封 IP"),
        _("健康状态"),
    )
    return HttpResponse(html)


@csrf_protect
@api_permission_required("django_ip_safeguard.view_ipaccesslog")
@require_GET
def dashboard_api_view(request: HttpRequest) -> JsonResponse:
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


@csrf_protect
@api_permission_required(
    "django_ip_safeguard.view_ipguardpolicy",
    "django_ip_safeguard.change_ipguardpolicy",
    any_perm=True,
)
@require_http_methods(["GET", "POST"])
def policy_view(request: HttpRequest) -> JsonResponse:
    if request.method == "GET" and not request.user.has_perm("django_ip_safeguard.view_ipguardpolicy"):
        return api_error(_("权限不足：缺少策略查看权限"), code=4031, status=403)
    if request.method == "POST" and not request.user.has_perm("django_ip_safeguard.change_ipguardpolicy"):
        return api_error(_("权限不足：缺少策略修改权限"), code=4031, status=403)

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
                "ip_blacklist": policy.ip_blacklist,
                "rate_limit_per_minute": policy.rate_limit_per_minute,
                "fail_open": policy.fail_open,
                "fail_open_path_prefixes": policy.fail_open_path_prefixes,
                "fail_close_path_prefixes": policy.fail_close_path_prefixes,
                "block_status_code": policy.block_status_code,
                "cache_ttl": policy.cache_ttl,
                "ban_ttl": policy.ban_ttl,
                "use_db_log": policy.use_db_log,
                "china_pool_rule": getattr(policy, "china_pool_rule", "off"),
                "international_pool_rule": getattr(policy, "international_pool_rule", "off"),
                "updated_at": policy.updated_at.isoformat(),
                "pool_feed_urls": {
                    "geo_china_pool_url": get_settings().geo_china_pool_url,
                    "geo_international_pool_url": get_settings().geo_international_pool_url,
                },
            }
        )

    try:
        payload = _load_json_body(request)
    except json.JSONDecodeError:
        return api_error(_("JSON 格式错误"), code=4001, status=400)

    if "rate_limit_per_minute" in payload:
        try:
            rl = int(payload["rate_limit_per_minute"])
        except (TypeError, ValueError):
            return api_error(_("rate_limit_per_minute 必须为整数"), code=4006, status=400)
        if rl < 0 or rl > 100000:
            return api_error(_("rate_limit_per_minute 范围为 0～100000（0 表示关闭）"), code=4006, status=400)
        policy.rate_limit_per_minute = rl

    list_json_fields = {
        "blocked_risk_tags",
        "allowed_countries",
        "blocked_countries",
        "ip_whitelist",
        "ip_blacklist",
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
        "ip_blacklist",
        "fail_open",
        "fail_open_path_prefixes",
        "fail_close_path_prefixes",
        "block_status_code",
        "cache_ttl",
        "ban_ttl",
        "use_db_log",
        "china_pool_rule",
        "international_pool_rule",
    ]
    for field in editable_fields:
        if field not in payload:
            continue
        val = payload[field]
        if field in list_json_fields and not isinstance(val, list):
            return api_error(_("字段 %(field)s 必须为 JSON 数组") % {"field": field}, code=4005, status=400)
        if field in {"allowed_countries", "blocked_countries"}:
            normalized, err = _normalize_country_codes(val, field)
            if err:
                return err
            val = normalized
        elif field in {"ip_whitelist", "ip_blacklist"}:
            normalized, err = _normalize_ip_rules(val, field)
            if err:
                return err
            val = normalized
        elif field in {"blocked_risk_tags", "fail_open_path_prefixes", "fail_close_path_prefixes"}:
            val = _normalize_string_list(val)
        elif field in {"china_pool_rule", "international_pool_rule"}:
            val = str(val).strip().lower()
            if val not in GEO_POOL_RULE_CHOICES:
                return api_error(
                    _("字段 %(field)s 须为 off、allow_only_in_pool 或 block_in_pool") % {"field": field},
                    code=4012,
                    status=400,
                )
        setattr(policy, field, val)
    policy.save()
    invalidate_policy_cache()
    return api_success({"name": policy.name}, message=_("策略已更新"))


@csrf_protect
@api_permission_required("django_ip_safeguard.change_ipbanrecord")
@require_http_methods(["POST"])
def unban_ip_view(request: HttpRequest) -> JsonResponse:
    try:
        payload = _load_json_body(request)
    except json.JSONDecodeError:
        return api_error(_("JSON 格式错误"), code=4001, status=400)
    ip = str(payload.get("ip", "")).strip()
    if not ip:
        return api_error(_("ip 参数不能为空"), code=4002, status=400)

    cfg = get_settings()
    cache_service = RedisCacheService(cfg.redis_url)
    cache_service.unban(ip)
    IpBanRecord.objects.filter(ip=ip).update(is_active=False, expired_at=timezone.now())
    return api_success({"ip": ip}, message=_("解封成功"))


@csrf_protect
@api_permission_required("django_ip_safeguard.change_ipbanrecord")
@require_http_methods(["POST"])
def ban_ip_view(request: HttpRequest) -> JsonResponse:
    try:
        payload = _load_json_body(request)
    except json.JSONDecodeError:
        return api_error(_("JSON 格式错误"), code=4001, status=400)

    ip = str(payload.get("ip", "")).strip()
    reason = str(payload.get("reason", "manual_ban")).strip()[:255]
    ttl = int(payload.get("ttl", 86400))
    if not ip:
        return api_error(_("ip 参数不能为空"), code=4002, status=400)

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
    return api_success({"ip": ip, "ttl": max(60, ttl)}, message=_("封禁成功"))


@csrf_protect
@api_permission_required("django_ip_safeguard.view_ipbanrecord")
@require_GET
def ban_list_view(request: HttpRequest) -> JsonResponse:
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


@csrf_protect
@api_permission_required("django_ip_safeguard.view_ipaccesslog")
@require_GET
def access_log_list_view(request: HttpRequest) -> JsonResponse:
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
    def write(self, value):
        return value


@csrf_protect
@api_permission_required("django_ip_safeguard.view_ipaccesslog")
@require_GET
def access_log_export_view(request: HttpRequest) -> StreamingHttpResponse:
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


@csrf_protect
@api_permission_required(
    "django_ip_safeguard.view_ipaccesslog",
    "django_ip_safeguard.view_ipbanrecord",
    any_perm=True,
)
@require_GET
def recent_records_view(request: HttpRequest) -> JsonResponse:
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


@csrf_protect
@api_permission_required("django_ip_safeguard.view_ipguardpolicy")
@require_GET
def health_view(request: HttpRequest) -> JsonResponse:
    cfg = get_settings()
    cache_service = RedisCacheService(cfg.redis_url)
    t0 = time.perf_counter()
    redis_ok = cache_service.ping()
    redis_latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    base_info = {
        "service": "django-ip-safeguard",
        "status": "healthy" if redis_ok else "degraded",
        "redis_ok": redis_ok,
    }

    user = _resolve_request_user(request)
    show_detail = user.is_superuser or user.has_perm("django_ip_safeguard.view_ipguardpolicy")

    if not show_detail:
        return api_success(base_info)

    pool_rows = []
    for row in IpGeoPoolStatus.objects.all().order_by("pool_key"):
        pool_rows.append(
            {
                "pool_key": row.pool_key,
                "line_count": row.line_count,
                "v4_interval_count": row.v4_interval_count,
                "v6_net_count": row.v6_net_count,
                "last_ok_at": row.last_ok_at.isoformat() if row.last_ok_at else None,
                "last_error": (row.last_error or "")[:200],
            }
        )

    return api_success(
        {
            **base_info,
            "redis_latency_ms": redis_latency_ms,
            "provider": cfg.provider,
            "policy_center_enabled": cfg.enable_policy_center,
            "geo_ip_pools": pool_rows,
            "geo_pool_configured": {
                "china": bool(cfg.geo_china_pool_url),
                "international": bool(cfg.geo_international_pool_url),
            },
        }
    )


@csrf_protect
@api_permission_required("django_ip_safeguard.view_ipguardpolicy")
@require_GET
def geo_pools_status_view(request: HttpRequest) -> JsonResponse:
    cfg = get_settings()
    rows = []
    for row in IpGeoPoolStatus.objects.all().order_by("pool_key"):
        rows.append(
            {
                "pool_key": row.pool_key,
                "source_url": row.source_url,
                "line_count": row.line_count,
                "v4_interval_count": row.v4_interval_count,
                "v6_net_count": row.v6_net_count,
                "last_ok_at": row.last_ok_at.isoformat() if row.last_ok_at else None,
                "last_error": row.last_error or "",
            }
        )
    return api_success(
        {
            "pools": rows,
            "feed_urls": {
                "china": cfg.geo_china_pool_url,
                "international": cfg.geo_international_pool_url or "",
            },
            "rule_choices": sorted(GEO_POOL_RULE_CHOICES),
        }
    )


@csrf_protect
@api_permission_required("django_ip_safeguard.change_ipguardpolicy")
@require_http_methods(["POST"])
def geo_pools_sync_view(request: HttpRequest) -> JsonResponse:
    summary = sync_all_geo_pools(get_settings())
    return api_success(summary, message=_("同步任务已执行"))


@csrf_protect
@api_permission_required()
@require_GET
def auth_me_view(request: HttpRequest) -> JsonResponse:
    user = _resolve_request_user(request)
    return api_success(
        {
            "username": user.username,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "groups": list(user.groups.values_list("name", flat=True)),
            "permissions": sorted(user.get_all_permissions()),
        }
    )


@ensure_csrf_cookie
@csrf_protect
@require_GET
def csrf_view(_request: HttpRequest) -> JsonResponse:
    return api_success({"csrf": "ok"})


@csrf_protect
@require_http_methods(["POST"])
def login_view(request: HttpRequest) -> JsonResponse:
    try:
        payload = _load_json_body(request)
    except json.JSONDecodeError:
        return api_error(_("JSON 格式错误"), code=4001, status=400)

    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    if not username or not password:
        return api_error(_("用户名或密码不能为空"), code=4003, status=400)
    user = authenticate(request, username=username, password=password)
    if not user:
        return api_error(_("用户名或密码错误"), code=4004, status=401)
    if not user.is_staff:
        return api_error(_("该账号无后台权限"), code=4030, status=403)
    login(request, user)
    return api_success({"username": user.username}, message=_("登录成功"))


@require_http_methods(["POST"])
@csrf_protect
def jwt_login_view(request: HttpRequest) -> JsonResponse:
    try:
        payload = _load_json_body(request)
    except json.JSONDecodeError:
        return api_error(_("JSON 格式错误"), code=4001, status=400)
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    if not username or not password:
        return api_error(_("用户名或密码不能为空"), code=4003, status=400)
    user = authenticate(request, username=username, password=password)
    if not user:
        return api_error(_("用户名或密码错误"), code=4004, status=401)
    if not user.is_staff:
        return api_error(_("该账号无后台权限"), code=4030, status=403)
    return api_success(issue_token_pair(user), message=_("JWT 登录成功"))


@require_http_methods(["POST"])
@csrf_protect
def jwt_refresh_view(request: HttpRequest) -> JsonResponse:
    try:
        payload = _load_json_body(request)
    except json.JSONDecodeError:
        return api_error(_("JSON 格式错误"), code=4001, status=400)
    refresh_token = str(payload.get("refresh_token", "")).strip()
    if not refresh_token:
        return api_error(_("refresh_token 不能为空"), code=4009, status=400)
    refreshed = refresh_access_token(refresh_token)
    if not refreshed:
        return api_error(_("refresh_token 无效或已过期"), code=4011, status=401)
    return api_success(refreshed, message=_("刷新成功"))


@login_required
@csrf_protect
@require_http_methods(["POST"])
def logout_view(request: HttpRequest) -> JsonResponse:
    logout(request)
    return api_success(message=_("已退出登录"))


@require_http_methods(["POST"])
@csrf_protect
def jwt_logout_view(_request: HttpRequest) -> JsonResponse:
    return api_success(message=_("JWT 已退出（请客户端删除本地 token）"))
