import json
from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from django_ip_safeguard.conf import get_settings
from django_ip_safeguard.models import IpAccessLog, IpGuardPolicy
from django_ip_safeguard.services.cache import RedisCacheService
from django_ip_safeguard.services.policy_service import invalidate_policy_cache


def _load_json_body(request: HttpRequest) -> dict:
    raw = request.body.decode("utf-8").strip()
    if not raw:
        return {}
    return json.loads(raw)


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

    return JsonResponse(
        {
            "total_count_24h": total_count,
            "block_count_24h": blocked_count,
            "allow_count_24h": allow_count,
            "top_risk_ips": top_risk_ips,
            "country_distribution": country_distribution,
        }
    )


@staff_member_required
@require_http_methods(["GET", "POST"])
def policy_view(request: HttpRequest) -> JsonResponse:
    """策略中心读取与更新接口。"""

    policy, _created = IpGuardPolicy.objects.get_or_create(name="default")
    if request.method == "GET":
        return JsonResponse(
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
        return JsonResponse({"detail": "JSON 格式错误"}, status=400)
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
        if field in payload:
            setattr(policy, field, payload[field])
    policy.save()
    invalidate_policy_cache()
    return JsonResponse({"detail": "策略已更新"})


@staff_member_required
@require_http_methods(["POST"])
def unban_ip_view(request: HttpRequest) -> JsonResponse:
    """手动解封 IP。"""

    try:
        payload = _load_json_body(request)
    except json.JSONDecodeError:
        return JsonResponse({"detail": "JSON 格式错误"}, status=400)
    ip = str(payload.get("ip", "")).strip()
    if not ip:
        return JsonResponse({"detail": "ip 参数不能为空"}, status=400)

    cfg = get_settings()
    cache_service = RedisCacheService(cfg.redis_url)
    cache_service.unban(ip)
    return JsonResponse({"detail": "解封成功", "ip": ip})


@staff_member_required
@require_GET
def health_view(request: HttpRequest) -> JsonResponse:
    """插件健康状态接口。"""

    cfg = get_settings()
    cache_service = RedisCacheService(cfg.redis_url)
    redis_ok = cache_service.ping()
    return JsonResponse(
        {
            "service": "django-ip-safeguard",
            "redis_ok": redis_ok,
            "provider": cfg.provider,
            "policy_center_enabled": cfg.enable_policy_center,
        }
    )
