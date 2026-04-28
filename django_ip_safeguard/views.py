import csv
import hashlib
import ipaddress
import json
import secrets
import time
from datetime import datetime, time as dt_time, timedelta
from functools import wraps
from typing import Dict, List, Optional, Tuple

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
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
from django_ip_safeguard.models import (
    IpAccessLog,
    IpBanRecord,
    IpGeoPoolStatus,
    IpGuardPolicy,
    IpGuardPolicySnapshot,
    ScheduledTask,
    TaskExecutionLog,
    UserProfile,
)
from django_ip_safeguard.services.audit_service import mask_ip
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


def _get_client_ip(request: HttpRequest) -> str:
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")


def _log_security_audit(request: HttpRequest, action: str, detail: str = "", user=None) -> None:
    try:
        from django_ip_safeguard.models import IpAccessLog
        ip = _get_client_ip(request)
        IpAccessLog.objects.create(
            ip=ip,
            country_code="",
            country_name="",
            region="",
            city="",
            asn=0,
            asn_org="",
            is_datacenter=False,
            is_proxy=False,
            is_vpn=False,
            is_tor=False,
            risk_score=0,
            risk_tags="",
            decision="security_audit",
            reason=f"[{action}] {detail}"[:255],
            path=f"/security-audit/{action}"[:255],
        )
    except Exception:
        pass


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


def _get_user_profile(user) -> UserProfile:
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


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


def _access_log_to_dict(item: IpAccessLog, mask_enabled: bool = False, mask_keep_prefix: int = 2) -> dict:
    return {
        "ip": mask_ip(item.ip, mask_enabled, mask_keep_prefix),
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


@csrf_protect
@api_permission_required("django_ip_safeguard.view_ipaccesslog")
@require_GET
def dashboard_api_view(request: HttpRequest) -> JsonResponse:
    cache_key = "dashboard:api:24h"
    try:
        cache_svc = RedisCacheService(get_settings().redis_url)
        cached = cache_svc.client.get(cache_key)
        if cached is not None:
            import json as _json
            return api_success(_json.loads(cached))
    except Exception:
        pass

    cfg = get_settings()
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
    for row in top_risk_ips:
        row["ip"] = mask_ip(row["ip"], cfg.ip_mask_enabled, cfg.ip_mask_keep_prefix)
    country_distribution = list(
        today_logs.exclude(country_code="")
        .exclude(country_code="UNKNOWN")
        .exclude(country_code="LOCAL")
        .values("country_code")
        .annotate(
            count=Count("id"),
            blocked=Count("id", filter=Q(decision="block")),
            allowed=Count("id", filter=Q(decision="allow")),
        )
        .order_by("-count")[:30]
    )
    country_name_map = dict(
        today_logs.exclude(country_code="")
        .exclude(country_code="UNKNOWN")
        .exclude(country_code="LOCAL")
        .values_list("country_code", "country_name")
        .distinct()
    )
    for row in country_distribution:
        row["country_name"] = country_name_map.get(row["country_code"], row["country_code"])
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

    result_data = {
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

    try:
        cache_svc = RedisCacheService(get_settings().redis_url)
        cache_svc.client.setex(cache_key, 120, json.dumps(result_data))
    except Exception:
        pass

    return api_success(result_data)


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
        return api_success(_serialize_policy(policy))

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

    err = _apply_policy_payload(policy, payload)
    if err is not None:
        return err

    before_snapshot = _serialize_policy(policy, with_meta=False)
    policy.save()
    after_snapshot = _serialize_policy(policy, with_meta=False)
    try:
        IpGuardPolicySnapshot.objects.create(
            policy=policy,
            actor=request.user if getattr(request.user, "is_authenticated", False) else None,
            before_json=before_snapshot,
            after_json=after_snapshot,
        )
    except Exception:  # noqa: BLE001
        # 快照失败不影响策略保存主流程
        pass
    invalidate_policy_cache()
    return api_success({"name": policy.name}, message=_("策略已更新"))


_POLICY_ACTION_VALUES = frozenset({"allow", "log_only", "rate_limit", "challenge", "block", "ban"})


def _serialize_policy(policy, with_meta: bool = True) -> dict:
    data = {
        "name": policy.name,
        "enabled": policy.enabled,
        "priority": int(getattr(policy, "priority", 10000) or 10000),
        "match_host_regex": getattr(policy, "match_host_regex", "") or "",
        "match_path_prefixes": list(getattr(policy, "match_path_prefixes", []) or []),
        "match_methods": list(getattr(policy, "match_methods", []) or []),
        "tier_thresholds": dict(getattr(policy, "tier_thresholds", {}) or {}),
        "signal_weights": dict(getattr(policy, "signal_weights", {}) or {}),
        "medium_action": getattr(policy, "medium_action", "block") or "block",
        "high_action": getattr(policy, "high_action", "ban") or "ban",
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
    }
    if with_meta:
        data["updated_at"] = policy.updated_at.isoformat()
        data["pool_feed_urls"] = {
            "geo_china_pool_url": get_settings().geo_china_pool_url,
            "geo_international_pool_url": get_settings().geo_international_pool_url,
        }
    return data


def _apply_policy_payload(policy, payload: dict):
    """把 JSON payload 校验后写到 policy 实例上；出错返回 JsonResponse，成功返回 None。"""
    list_json_fields = {
        "blocked_risk_tags",
        "allowed_countries",
        "blocked_countries",
        "ip_whitelist",
        "ip_blacklist",
        "fail_open_path_prefixes",
        "fail_close_path_prefixes",
        "match_path_prefixes",
        "match_methods",
    }
    dict_json_fields = {"tier_thresholds", "signal_weights"}
    editable_fields = [
        "enabled",
        "priority",
        "match_host_regex",
        "match_path_prefixes",
        "match_methods",
        "tier_thresholds",
        "signal_weights",
        "medium_action",
        "high_action",
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
        if field in dict_json_fields and not isinstance(val, dict):
            return api_error(_("字段 %(field)s 必须为 JSON 对象") % {"field": field}, code=4005, status=400)
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
        elif field in {
            "blocked_risk_tags",
            "fail_open_path_prefixes",
            "fail_close_path_prefixes",
            "match_path_prefixes",
        }:
            val = _normalize_string_list(val)
        elif field == "match_methods":
            val = [str(x).strip().upper() for x in val if str(x).strip()]
        elif field in {"china_pool_rule", "international_pool_rule"}:
            val = str(val).strip().lower()
            if val not in GEO_POOL_RULE_CHOICES:
                return api_error(
                    _("字段 %(field)s 须为 off、allow_only_in_pool 或 block_in_pool") % {"field": field},
                    code=4012,
                    status=400,
                )
        elif field in {"medium_action", "high_action"}:
            val = str(val).strip().lower()
            if val not in _POLICY_ACTION_VALUES:
                return api_error(
                    _("字段 %(field)s 须为 %(values)s 之一") % {
                        "field": field,
                        "values": ", ".join(sorted(_POLICY_ACTION_VALUES)),
                    },
                    code=4013,
                    status=400,
                )
        elif field == "priority":
            try:
                val = int(val)
            except (TypeError, ValueError):
                return api_error(_("priority 必须为整数"), code=4014, status=400)
        setattr(policy, field, val)
    return None


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

    cfg = get_settings()
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    items = [_access_log_to_dict(item, mask_enabled=cfg.ip_mask_enabled, mask_keep_prefix=cfg.ip_mask_keep_prefix) for item in page_obj.object_list]
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

    cfg = get_settings()
    pseudo_buffer = _Echo()

    def rows():
        writer = csv.writer(pseudo_buffer)
        yield "\ufeff"
        yield writer.writerow(["ip", "country_code", "risk_score", "risk_tags", "decision", "reason", "path", "created_at"])
        for item in queryset:
            yield writer.writerow(
                [
                    mask_ip(item.ip, cfg.ip_mask_enabled, cfg.ip_mask_keep_prefix),
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

    cfg = get_settings()
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
            "recent_attacks": [_access_log_to_dict(x, mask_enabled=cfg.ip_mask_enabled, mask_keep_prefix=cfg.ip_mask_keep_prefix) for x in attack_qs],
            "recent_access": [_access_log_to_dict(x, mask_enabled=cfg.ip_mask_enabled, mask_keep_prefix=cfg.ip_mask_keep_prefix) for x in access_qs],
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
    profile = _get_user_profile(user) if user.is_authenticated else None
    return api_success(
        {
            "username": user.username,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "groups": list(user.groups.values_list("name", flat=True)),
            "permissions": sorted(user.get_all_permissions()),
            "language": profile.language if profile else "zh-hans",
            "two_factor_enabled": profile.two_factor_enabled if profile else False,
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

    client_ip = _get_client_ip(request)
    from django_ip_safeguard.services.login_throttle import check_login_throttle, record_login_failure, clear_login_failures
    throttle = check_login_throttle(client_ip, username)
    if throttle:
        ttl, max_f = throttle
        return api_error(_("登录失败次数过多，请 %(ttl)s 秒后重试") % {"ttl": ttl}, code=4290, status=429)

    user = authenticate(request, username=username, password=password)
    if not user:
        record_login_failure(client_ip, username)
        return api_error(_("用户名或密码错误"), code=4004, status=401)
    if not user.is_staff:
        return api_error(_("该账号无后台权限"), code=4030, status=403)

    profile = _get_user_profile(user)
    from django.conf import settings as django_settings
    password_max_age = getattr(django_settings, "IP_GUARD_PASSWORD_MAX_AGE_DAYS", 0)
    if profile.is_password_expired(password_max_age):
        return api_error(_("密码已过期，请先修改密码"), code=4012, status=401, data={"password_expired": True})

    clear_login_failures(client_ip, username)

    if profile.two_factor_enabled:
        request.session["2fa_pending_user_id"] = user.id
        request.session["2fa_pending_ts"] = time.time()
        return api_success({"2fa_required": True, "username": user.username}, message=_("需要双因素认证验证"))
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

    client_ip = _get_client_ip(request)
    from django_ip_safeguard.services.login_throttle import check_login_throttle, record_login_failure, clear_login_failures
    throttle = check_login_throttle(client_ip, username)
    if throttle:
        ttl, max_f = throttle
        return api_error(_("登录失败次数过多，请 %(ttl)s 秒后重试") % {"ttl": ttl}, code=4290, status=429)

    user = authenticate(request, username=username, password=password)
    if not user:
        record_login_failure(client_ip, username)
        return api_error(_("用户名或密码错误"), code=4004, status=401)
    if not user.is_staff:
        return api_error(_("该账号无后台权限"), code=4030, status=403)

    profile = _get_user_profile(user)
    from django.conf import settings as django_settings
    password_max_age = getattr(django_settings, "IP_GUARD_PASSWORD_MAX_AGE_DAYS", 0)
    if profile.is_password_expired(password_max_age):
        return api_error(_("密码已过期，请先修改密码"), code=4012, status=401, data={"password_expired": True})

    clear_login_failures(client_ip, username)

    if profile.two_factor_enabled:
        request.session["2fa_pending_user_id"] = user.id
        request.session["2fa_pending_ts"] = time.time()
        return api_success({"2fa_required": True, "username": user.username}, message=_("需要双因素认证验证"))
    return api_success(issue_token_pair(user), message=_("JWT 登录成功"))


@csrf_protect
@require_http_methods(["POST"])
def two_factor_login_verify_view(request: HttpRequest) -> JsonResponse:
    try:
        payload = _load_json_body(request)
    except json.JSONDecodeError:
        return api_error(_("JSON 格式错误"), code=4001, status=400)
    code = str(payload.get("code", "")).strip()
    if not code:
        return api_error(_("验证码不能为空"), code=4002, status=400)
    pending_id = request.session.get("2fa_pending_user_id")
    pending_ts = request.session.get("2fa_pending_ts")
    if not pending_id or not pending_ts:
        return api_error(_("请先完成用户名密码登录"), code=4010, status=401)
    if time.time() - pending_ts > 300:
        request.session.pop("2fa_pending_user_id", None)
        request.session.pop("2fa_pending_ts", None)
        return api_error(_("2FA 验证已超时，请重新登录"), code=4010, status=401)
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        user = User.objects.get(pk=pending_id)
    except User.DoesNotExist:
        return api_error(_("用户不存在"), code=4010, status=401)
    profile = _get_user_profile(user)
    if not profile.two_factor_enabled:
        return api_error(_("该用户未启用 2FA"), code=4008, status=400)
    if profile.is_2fa_locked():
        remaining = profile.get_2fa_lock_remaining_seconds()
        return api_error(
            _("2FA 验证失败次数过多，账户已锁定，请 %(ttl)s 秒后重试") % {"ttl": remaining},
            code=4291,
            status=429,
        )
    try:
        import pyotp
    except ImportError:
        return api_error(_("2FA 功能未安装 pyotp 依赖"), code=5001, status=500)
    secret = profile.two_factor_secret
    if not secret:
        return api_error(_("2FA 密钥未设置"), code=4008, status=400)
    totp = pyotp.totp.TOTP(secret)
    verified = totp.verify(code, valid_window=1)
    if not verified:
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        if code_hash in (profile.recovery_codes or []):
            verified = True
            profile.recovery_codes = [h for h in profile.recovery_codes if h != code_hash]
            profile.save(update_fields=["recovery_codes"])
    if not verified:
        profile.record_2fa_failure()
        return api_error(_("验证码不正确"), code=4004, status=400)
    profile.clear_2fa_failure()
    request.session.pop("2fa_pending_user_id", None)
    request.session.pop("2fa_pending_ts", None)
    login_mode = str(payload.get("login_mode", "session")).strip().lower()
    if login_mode == "jwt":
        return api_success(issue_token_pair(user), message=_("2FA 验证成功，JWT 登录成功"))
    login(request, user)
    return api_success({"username": user.username}, message=_("2FA 验证成功，登录成功"))


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


@require_GET
def i18n_lang_list_view(request: HttpRequest) -> JsonResponse:
    from django.conf import settings
    languages = getattr(settings, "LANGUAGES", [("zh-hans", "简体中文"), ("en", "English")])
    current = getattr(request, "LANGUAGE_CODE", "zh-hans")
    return api_success({
        "languages": [{"code": code, "name": name} for code, name in languages],
        "current": current,
    })


@require_http_methods(["POST"])
def i18n_lang_switch_view(request: HttpRequest) -> JsonResponse:
    from django.conf import settings
    from django.utils.translation import activate
    try:
        payload = _load_json_body(request)
    except json.JSONDecodeError:
        return api_error(_("JSON 格式错误"), code=4001, status=400)
    lang_code = str(payload.get("language", "")).strip().lower()
    supported = dict(getattr(settings, "LANGUAGES", {}))
    if lang_code not in supported:
        return api_error(_("不支持的语言代码"), code=4007, status=400)
    activate(lang_code)
    if hasattr(request, "session") and request.session.session_key:
        request.session["django_language"] = lang_code
    user = _resolve_request_user(request)
    if user.is_authenticated:
        profile = _get_user_profile(user)
        profile.language = lang_code
        profile.save(update_fields=["language"])
    response = api_success({"language": lang_code}, message=_("语言已切换"))
    response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang_code, max_age=settings.LANGUAGE_COOKIE_AGE)
    return response


@csrf_protect
@api_permission_required()
@require_http_methods(["POST"])
def change_password_view(request: HttpRequest) -> JsonResponse:
    try:
        payload = _load_json_body(request)
    except json.JSONDecodeError:
        return api_error(_("JSON 格式错误"), code=4001, status=400)
    user = _resolve_request_user(request)
    if not user.is_authenticated:
        return api_error(_("未登录"), code=4010, status=401)
    old_password = str(payload.get("old_password", ""))
    new_password = str(payload.get("new_password", ""))
    if not old_password or not new_password:
        return api_error(_("旧密码和新密码不能为空"), code=4002, status=400)
    if len(new_password) < 8:
        return api_error(_("新密码长度不能少于8位"), code=4002, status=400)
    has_upper = any(c.isupper() for c in new_password)
    has_lower = any(c.islower() for c in new_password)
    has_digit = any(c.isdigit() for c in new_password)
    has_special = any(not c.isalnum() for c in new_password)
    complexity_count = sum([has_upper, has_lower, has_digit, has_special])
    if complexity_count < 3:
        return api_error(_("新密码需包含大写字母、小写字母、数字、特殊字符中的至少3种"), code=4002, status=400)
    if not user.check_password(old_password):
        return api_error(_("旧密码不正确"), code=4004, status=400)
    user.set_password(new_password)
    user.save(update_fields=["password"])
    profile = _get_user_profile(user)
    profile.password_changed_at = timezone.now()
    profile.save(update_fields=["password_changed_at"])
    _log_security_audit(request, "password_change", f"user={user.username}", user)
    return api_success(message=_("密码修改成功"))


@csrf_protect
@api_permission_required()
@require_http_methods(["POST"])
def change_email_view(request: HttpRequest) -> JsonResponse:
    try:
        payload = _load_json_body(request)
    except json.JSONDecodeError:
        return api_error(_("JSON 格式错误"), code=4001, status=400)
    user = _resolve_request_user(request)
    if not user.is_authenticated:
        return api_error(_("未登录"), code=4010, status=401)
    new_email = str(payload.get("email", "")).strip()
    if not new_email:
        return api_error(_("邮箱不能为空"), code=4002, status=400)
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError as DjangoValidationError
    try:
        validate_email(new_email)
    except DjangoValidationError:
        return api_error(_("邮箱格式不正确"), code=4002, status=400)
    if new_email == user.email:
        return api_error(_("新邮箱与当前邮箱相同"), code=4002, status=400)

    profile = _get_user_profile(user)
    token = UserProfile.generate_email_token()
    profile.pending_email = new_email
    profile.email_verification_token = token
    profile.email_token_expires = timezone.now() + timedelta(hours=24)
    profile.save(update_fields=["pending_email", "email_verification_token", "email_token_expires"])

    from django_ip_safeguard.services.email_service import send_verification_email
    email_sent = send_verification_email(new_email, token, user.username)
    _log_security_audit(request, "email_change_request", f"user={user.username} pending_email={new_email}", user)

    if email_sent:
        return api_success({"pending_email": new_email, "email_sent": True}, message=_("验证邮件已发送，请查收邮箱并点击验证链接"))
    else:
        return api_success({"pending_email": new_email, "email_sent": False}, message=_("邮件发送失败，请联系管理员"))


@csrf_protect
@require_http_methods(["GET"])
def verify_email_view(request: HttpRequest) -> JsonResponse:
    token = str(request.GET.get("token", "")).strip()
    if not token:
        return api_error(_("验证令牌不能为空"), code=4002, status=400)
    profile = UserProfile.objects.filter(email_verification_token=token).first()
    if not profile:
        return api_error(_("验证令牌无效"), code=4004, status=400)
    if not profile.is_email_token_valid():
        return api_error(_("验证令牌已过期，请重新申请"), code=4010, status=400)
    if not profile.pending_email:
        return api_error(_("没有待验证的邮箱"), code=4004, status=400)
    user = profile.user
    user.email = profile.pending_email
    user.save(update_fields=["email"])
    profile.pending_email = ""
    profile.email_verification_token = ""
    profile.email_token_expires = None
    profile.save(update_fields=["pending_email", "email_verification_token", "email_token_expires"])
    _log_security_audit(request, "email_change_confirm", f"user={user.username} email={user.email}", user)
    return api_success({"email": user.email}, message=_("邮箱验证成功"))


@csrf_protect
@api_permission_required()
@require_GET
def two_factor_status_view(request: HttpRequest) -> JsonResponse:
    user = _resolve_request_user(request)
    if not user.is_authenticated:
        return api_error(_("未登录"), code=4010, status=401)
    profile = _get_user_profile(user)
    locked = profile.is_2fa_locked()
    return api_success({
        "enabled": profile.two_factor_enabled,
        "locked": locked,
        "lock_remaining_seconds": profile.get_2fa_lock_remaining_seconds() if locked else 0,
        "fail_count": profile.two_factor_fail_count,
    })


@csrf_protect
@api_permission_required()
@require_http_methods(["POST"])
def two_factor_setup_view(request: HttpRequest) -> JsonResponse:
    user = _resolve_request_user(request)
    if not user.is_authenticated:
        return api_error(_("未登录"), code=4010, status=401)
    try:
        import pyotp
    except ImportError:
        return api_error(_("2FA 功能未安装 pyotp 依赖"), code=5001, status=500)
    secret = pyotp.random_base32()
    profile = _get_user_profile(user)
    profile.two_factor_secret = secret
    profile.two_factor_enabled = False
    profile.clear_2fa_failure()
    profile.save(update_fields=["two_factor_secret", "two_factor_enabled", "two_factor_fail_count", "two_factor_locked_until"])
    provisioning_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=user.email or user.username, issuer_name="IP Guard"
    )
    return api_success({"secret": secret, "provisioning_uri": provisioning_uri})


@csrf_protect
@api_permission_required()
@require_http_methods(["POST"])
def two_factor_verify_view(request: HttpRequest) -> JsonResponse:
    user = _resolve_request_user(request)
    if not user.is_authenticated:
        return api_error(_("未登录"), code=4010, status=401)
    try:
        payload = _load_json_body(request)
    except json.JSONDecodeError:
        return api_error(_("JSON 格式错误"), code=4001, status=400)
    code = str(payload.get("code", "")).strip()
    if not code:
        return api_error(_("验证码不能为空"), code=4002, status=400)
    try:
        import pyotp
    except ImportError:
        return api_error(_("2FA 功能未安装 pyotp 依赖"), code=5001, status=500)
    profile = _get_user_profile(user)
    secret = profile.two_factor_secret
    if not secret:
        return api_error(_("请先设置 2FA"), code=4008, status=400)
    totp = pyotp.totp.TOTP(secret)
    if not totp.verify(code, valid_window=1):
        return api_error(_("验证码不正确"), code=4004, status=400)

    recovery_codes = [secrets.token_hex(4).upper() for _ in range(8)]
    hashed_codes = [hashlib.sha256(rc.encode()).hexdigest() for rc in recovery_codes]
    profile.recovery_codes = hashed_codes
    profile.two_factor_enabled = True
    profile.clear_2fa_failure()
    profile.save(update_fields=["two_factor_enabled", "recovery_codes", "two_factor_fail_count", "two_factor_locked_until"])
    _log_security_audit(request, "2fa_enable", f"user={user.username}", user)
    return api_success({"recovery_codes": recovery_codes}, message=_("2FA 已启用，请妥善保存恢复码"))


@csrf_protect
@api_permission_required()
@require_http_methods(["POST"])
def two_factor_disable_view(request: HttpRequest) -> JsonResponse:
    user = _resolve_request_user(request)
    if not user.is_authenticated:
        return api_error(_("未登录"), code=4010, status=401)
    try:
        payload = _load_json_body(request)
    except json.JSONDecodeError:
        return api_error(_("JSON 格式错误"), code=4001, status=400)
    code = str(payload.get("code", "")).strip()
    if not code:
        return api_error(_("验证码不能为空"), code=4002, status=400)
    try:
        import pyotp
    except ImportError:
        return api_error(_("2FA 功能未安装 pyotp 依赖"), code=5001, status=500)
    profile = _get_user_profile(user)
    secret = profile.two_factor_secret
    if secret:
        totp = pyotp.totp.TOTP(secret)
        if not totp.verify(code, valid_window=1):
            return api_error(_("验证码不正确"), code=4004, status=400)
    profile.two_factor_secret = ""
    profile.two_factor_enabled = False
    profile.recovery_codes = []
    profile.clear_2fa_failure()
    profile.save(update_fields=["two_factor_secret", "two_factor_enabled", "recovery_codes", "two_factor_fail_count", "two_factor_locked_until"])
    _log_security_audit(request, "2fa_disable", f"user={user.username}", user)
    return api_success(message=_("2FA 已禁用"))


@csrf_protect
@require_http_methods(["POST"])
def api_key_login_view(request: HttpRequest) -> JsonResponse:
    try:
        payload = _load_json_body(request)
    except json.JSONDecodeError:
        return api_error(_("JSON 格式错误"), code=4001, status=400)
    api_key = str(payload.get("api_key", "")).strip()
    if not api_key:
        return api_error(_("API 密钥不能为空"), code=4002, status=400)
    from django_ip_safeguard.models import ApiKey, ApiKeyUsageLog
    key_hash = ApiKey.hash_key(api_key)
    client_ip = _get_client_ip(request)
    user_agent = request.META.get("HTTP_USER_AGENT", "")[:512]
    login_mode = str(payload.get("login_mode", "jwt")).strip().lower()
    try:
        obj = ApiKey.objects.select_related("user").get(key_hash=key_hash)
    except ApiKey.DoesNotExist:
        ApiKeyUsageLog.objects.create(
            ip=client_ip,
            user_agent=user_agent,
            action="login",
            success=False,
            failure_reason="invalid_key",
        )
        return api_error(_("API 密钥无效"), code=4004, status=401)
    is_valid, reason = obj.is_valid(client_ip)
    if not is_valid:
        obj.login_failures = min(obj.login_failures + 1, 10)
        obj.save(update_fields=["login_failures"])
        ApiKeyUsageLog.objects.create(
            api_key=obj,
            ip=client_ip,
            user_agent=user_agent,
            action="login",
            success=False,
            failure_reason=reason,
        )
        return api_error(reason, code=4004, status=401)
    user = obj.user
    if not user.is_active or not user.is_staff:
        obj.login_failures = min(obj.login_failures + 1, 10)
        obj.save(update_fields=["login_failures"])
        ApiKeyUsageLog.objects.create(
            api_key=obj,
            ip=client_ip,
            user_agent=user_agent,
            action="login",
            success=False,
            failure_reason="no_permission",
        )
        return api_error(_("该账号无后台权限"), code=4030, status=403)
    obj.last_used_at = timezone.now()
    obj.last_used_ip = client_ip
    obj.usage_count = obj.usage_count + 1
    obj.login_failures = 0
    obj.save(update_fields=["last_used_at", "last_used_ip", "usage_count", "login_failures"])
    ApiKeyUsageLog.objects.create(
        api_key=obj,
        user=user,
        ip=client_ip,
        user_agent=user_agent,
        action="login",
        success=True,
    )
    _log_security_audit(request, "api_key_login", f"user={user.username} key={obj.name} ip={client_ip}", user)
    if login_mode == "session":
        login(request, user)
        return api_success({"username": user.username}, message=_("API 密钥登录成功"))
    return api_success(issue_token_pair(user), message=_("API 密钥登录成功"))


@csrf_protect
@api_permission_required()
@require_GET
def api_key_list_view(request: HttpRequest) -> JsonResponse:
    user = _resolve_request_user(request)
    if not user.is_authenticated:
        return api_error(_("未登录"), code=4010, status=401)
    from django_ip_safeguard.models import ApiKey
    keys = ApiKey.objects.filter(user=user).order_by("-created_at")
    data = []
    for k in keys:
        data.append({
            "id": k.id,
            "name": k.name,
            "prefix": k.prefix,
            "is_active": k.is_active,
            "expires_at": k.expires_at.isoformat() if k.expires_at else None,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "last_used_ip": k.last_used_ip or None,
            "created_at": k.created_at.isoformat() if k.created_at else None,
            "allowed_ips": k.allowed_ips or [],
            "max_usage": k.max_usage,
            "usage_count": k.usage_count,
            "login_failures": k.login_failures,
        })
    return api_success(data)


@csrf_protect
@api_permission_required()
@require_http_methods(["POST"])
def api_key_create_view(request: HttpRequest) -> JsonResponse:
    user = _resolve_request_user(request)
    if not user.is_authenticated:
        return api_error(_("未登录"), code=4010, status=401)
    try:
        payload = _load_json_body(request)
    except json.JSONDecodeError:
        return api_error(_("JSON 格式错误"), code=4001, status=400)
    name = str(payload.get("name", "default")).strip()[:64]
    from django_ip_safeguard.models import ApiKey
    raw_key, prefix, key_hash = ApiKey.generate_key()
    expires_days = int(payload.get("expires_days", 0) or 0)
    expires_at = None
    if expires_days > 0:
        expires_at = timezone.now() + timedelta(days=expires_days)
    allowed_ips_raw = payload.get("allowed_ips", [])
    allowed_ips = []
    if isinstance(allowed_ips_raw, list):
        for ip in allowed_ips_raw:
            ip = str(ip).strip()
            if ip:
                allowed_ips.append(ip)
    max_usage = int(payload.get("max_usage", 0) or 0)
    client_ip = _get_client_ip(request)
    obj = ApiKey.objects.create(
        user=user,
        name=name,
        prefix=prefix,
        key_hash=key_hash,
        expires_at=expires_at,
        allowed_ips=allowed_ips,
        max_usage=max_usage,
        created_by_ip=client_ip,
    )
    _log_security_audit(request, "api_key_create", f"user={user.username} name={name} ip={client_ip}", user)
    return api_success({
        "id": obj.id,
        "name": obj.name,
        "key": raw_key,
        "prefix": obj.prefix,
        "expires_at": obj.expires_at.isoformat() if obj.expires_at else None,
        "created_at": obj.created_at.isoformat() if obj.created_at else None,
    }, message=_("API 密钥创建成功"))


@csrf_protect
@api_permission_required()
@require_http_methods(["POST"])
def api_key_revoke_view(request: HttpRequest) -> JsonResponse:
    user = _resolve_request_user(request)
    if not user.is_authenticated:
        return api_error(_("未登录"), code=4010, status=401)
    try:
        payload = _load_json_body(request)
    except json.JSONDecodeError:
        return api_error(_("JSON 格式错误"), code=4001, status=400)
    key_id = payload.get("id")
    if not key_id:
        return api_error(_("密钥 ID 不能为空"), code=4002, status=400)
    from django_ip_safeguard.models import ApiKey
    try:
        obj = ApiKey.objects.get(pk=key_id, user=user)
    except ApiKey.DoesNotExist:
        return api_error(_("密钥不存在"), code=4004, status=404)
    obj.is_active = False
    obj.save(update_fields=["is_active"])
    _log_security_audit(request, "api_key_revoke", f"user={user.username} key_id={key_id}", user)
    return api_success(message=_("API 密钥已吊销"))


@csrf_protect
@api_permission_required()
@require_http_methods(["POST"])
def api_key_logs_view(request: HttpRequest) -> JsonResponse:
    user = _resolve_request_user(request)
    if not user.is_authenticated:
        return api_error(_("未登录"), code=4010, status=401)
    try:
        payload = _load_json_body(request)
    except json.JSONDecodeError:
        return api_error(_("JSON 格式错误"), code=4001, status=400)
    key_id = payload.get("key_id")
    if not key_id:
        return api_error(_("密钥 ID 不能为空"), code=4002, status=400)
    from django_ip_safeguard.models import ApiKey, ApiKeyUsageLog
    try:
        obj = ApiKey.objects.get(pk=key_id, user=user)
    except ApiKey.DoesNotExist:
        return api_error(_("密钥不存在"), code=4004, status=404)
    page = max(1, int(payload.get("page", 1) or 1))
    page_size = min(100, max(10, int(payload.get("page_size", 20) or 20)))
    logs = ApiKeyUsageLog.objects.filter(api_key=obj).order_by("-created_at")
    total = logs.count()
    offset = (page - 1) * page_size
    logs = logs[offset:offset + page_size]
    data = []
    for log in logs:
        data.append({
            "id": log.id,
            "ip": log.ip or None,
            "user_agent": log.user_agent,
            "action": log.action,
            "success": log.success,
            "failure_reason": log.failure_reason,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })
    return api_success({"total": total, "page": page, "page_size": page_size, "logs": data})


@csrf_protect
@api_permission_required()
@require_GET
def user_profile_view(request: HttpRequest) -> JsonResponse:
    user = _resolve_request_user(request)
    if not user.is_authenticated:
        return api_error(_("未登录"), code=4010, status=401)
    profile = _get_user_profile(user)
    return api_success({
        "username": user.username,
        "email": user.email or "",
        "first_name": getattr(user, "first_name", ""),
        "last_name": getattr(user, "last_name", ""),
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "two_factor_enabled": profile.two_factor_enabled,
        "pending_email": profile.pending_email or "",
        "date_joined": user.date_joined.isoformat() if hasattr(user, "date_joined") and user.date_joined else None,
        "last_login": user.last_login.isoformat() if hasattr(user, "last_login") and user.last_login else None,
    })


@csrf_protect
@api_permission_required("django_ip_safeguard.view_ipaccesslog")
@require_GET
def user_stats_chart_view(request: HttpRequest) -> JsonResponse:
    days = _get_days_param(request, default=7, max_days=30)
    cache_key = f"chart:stats:{days}"
    try:
        cache_svc = RedisCacheService()
        cached = cache_svc.get(cache_key)
        if cached is not None:
            return api_success(cached)
    except Exception:
        pass

    since = timezone.now() - timedelta(days=days)

    daily_stats = list(
        IpAccessLog.objects.filter(created_at__gte=since)
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(
            total=Count("id"),
            blocked=Count("id", filter=Q(decision="block")),
            allowed=Count("id", filter=Q(decision="allow")),
        )
        .order_by("date")
    )
    for row in daily_stats:
        if row.get("date"):
            row["date"] = row["date"].isoformat()

    risk_distribution = list(
        IpAccessLog.objects.filter(created_at__gte=since)
        .extra(select={"risk_level": "CASE WHEN risk_score >= 70 THEN 'high' WHEN risk_score >= 40 THEN 'medium' ELSE 'low' END"})
        .values("risk_level")
        .annotate(count=Count("id"))
        .order_by("risk_level")
    )

    top_countries = list(
        IpAccessLog.objects.filter(created_at__gte=since)
        .values("country_code")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    hourly_pattern = list(
        IpAccessLog.objects.filter(created_at__gte=since)
        .annotate(hour=TruncHour("created_at"))
        .values("hour")
        .annotate(
            total=Count("id"),
            blocked=Count("id", filter=Q(decision="block")),
        )
        .order_by("hour")
    )
    for row in hourly_pattern:
        if row.get("hour"):
            row["hour"] = row["hour"].strftime("%H:00")

    result = {
        "daily_stats": daily_stats,
        "risk_distribution": risk_distribution,
        "top_countries": top_countries,
        "hourly_pattern": hourly_pattern,
        "days": days,
    }

    try:
        cache_svc = RedisCacheService()
        cache_svc.set(cache_key, result, timeout=300)
    except Exception:
        pass

    return api_success(result)


@csrf_protect
@api_permission_required("django_ip_safeguard.view_ipguardpolicy")
@require_http_methods(["GET", "POST"])
def system_settings_view(request: HttpRequest) -> JsonResponse:
    from django.conf import settings as django_settings
    cfg = get_settings()

    if request.method == "GET":
        policy, _ = IpGuardPolicy.objects.get_or_create(name="default")
        return api_success({
            # 可通过 API 修改的配置项（来自 IpGuardPolicy）
            "use_db_log": policy.use_db_log,
            "fail_open": policy.fail_open,
            "block_status_code": policy.block_status_code,
            "rate_limit_per_minute": policy.rate_limit_per_minute,
            "risk_score_threshold": policy.risk_score_threshold,
            "cache_ttl": policy.cache_ttl,
            "ban_ttl": policy.ban_ttl,
            "china_pool_rule": policy.china_pool_rule,
            "international_pool_rule": policy.international_pool_rule,
            # Django settings 配置项（只读）
            "enabled": cfg.enabled,
            "provider": cfg.provider,
            "provider_endpoint": cfg.provider_endpoint,
            "provider_timeout": cfg.provider_timeout,
            "provider_max_retries": cfg.provider_max_retries,
            "risk_score_threshold_max": 100,
            "rate_limit_max": 100000,
            "cache_ttl_min": 60,
            "ban_ttl_min": 60,
            "ip_mask_enabled": cfg.ip_mask_enabled,
            "ip_mask_keep_prefix": cfg.ip_mask_keep_prefix,
            "block_status_code_range": {"min": 400, "max": 499},
            # 分层缓存配置
            "l1_cache_enabled": cfg.l1_cache_enabled,
            "l1_cache_ttl": cfg.l1_cache_ttl,
            "l1_cache_max_size": cfg.l1_cache_max_size,
            # 本地风险规则引擎
            "local_risk_engine_enabled": cfg.local_risk_engine_enabled,
            "local_risk_subnet_attack_threshold": cfg.local_risk_subnet_attack_threshold,
            # 威胁情报订阅
            "threat_intel_enabled": cfg.threat_intel_enabled,
            "threat_intel_spamhaus_enabled": cfg.threat_intel_spamhaus_enabled,
            "threat_intel_tor_enabled": cfg.threat_intel_tor_enabled,
            "threat_intel_emerging_enabled": cfg.threat_intel_emerging_enabled,
            # IP 关联分析
            "ip_correlation_enabled": cfg.ip_correlation_enabled,
            # IP 信誉历史
            "ip_reputation_enabled": cfg.ip_reputation_enabled,
            "ip_reputation_snapshot_interval": cfg.ip_reputation_snapshot_interval,
            # GeoIP2 配置
            "geoip2_enabled": cfg.geoip2_enabled,
            "geoip2_city_db_path": cfg.geoip2_city_db_path,
            "geoip2_asn_db_path": cfg.geoip2_asn_db_path,
            # Provider Chain 配置
            "provider_chain_enabled": cfg.provider_chain_enabled,
            "provider_chain_names": list(cfg.provider_chain_names),
            # CIDR 多源备份
            "geo_pool_multi_source_enabled": cfg.geo_pool_multi_source_enabled,
            "geo_china_pool_url": cfg.geo_china_pool_url,
            "geo_international_pool_url": cfg.geo_international_pool_url,
            "geo_china_pool_backup_urls": list(cfg.geo_china_pool_backup_urls),
            "geo_international_pool_backup_urls": list(cfg.geo_international_pool_backup_urls),
            # 熔断器配置
            "provider_circuit_breaker_failures": cfg.provider_circuit_breaker_failures,
            "provider_circuit_breaker_ttl": cfg.provider_circuit_breaker_ttl,
            # 高低风险缓存
            "high_risk_cache_ttl": cfg.high_risk_cache_ttl,
            "low_risk_cache_ttl": cfg.low_risk_cache_ttl,
            # 防重放锁
            "dedupe_lock_seconds": cfg.dedupe_lock_seconds,
            # 认证配置
            "login_fail_limit": getattr(django_settings, "IP_GUARD_LOGIN_FAIL_LIMIT", 5),
            "login_fail_lock_seconds": getattr(django_settings, "IP_GUARD_LOGIN_FAIL_LOCK_SECONDS", 300),
            "password_max_age_days": getattr(django_settings, "IP_GUARD_PASSWORD_MAX_AGE_DAYS", 0),
            "jwt_access_token_ttl_seconds": cfg.jwt_access_token_ttl_seconds,
            "jwt_refresh_token_ttl_seconds": cfg.jwt_refresh_token_ttl_seconds,
        })

    try:
        payload = _load_json_body(request)
    except json.JSONDecodeError:
        return api_error(_("JSON 格式错误"), code=4001, status=400)

    policy, _created = IpGuardPolicy.objects.get_or_create(name="default")
    editable_mapping = {
        "use_db_log": "use_db_log",
        "fail_open": "fail_open",
        "block_status_code": "block_status_code",
        "rate_limit_per_minute": "rate_limit_per_minute",
        "risk_score_threshold": "risk_score_threshold",
        "cache_ttl": "cache_ttl",
        "ban_ttl": "ban_ttl",
        "china_pool_rule": "china_pool_rule",
        "international_pool_rule": "international_pool_rule",
    }
    for api_key, model_key in editable_mapping.items():
        if api_key in payload:
            val = payload[api_key]
            if api_key in ("china_pool_rule", "international_pool_rule"):
                val = str(val).strip().lower()
                if val not in GEO_POOL_RULE_CHOICES:
                    continue
            elif api_key == "block_status_code":
                val = int(val)
                if val < 400 or val > 499:
                    continue
            elif api_key == "rate_limit_per_minute":
                val = int(val)
                if val < 0 or val > 100000:
                    continue
            elif api_key == "risk_score_threshold":
                val = int(val)
                if val < 0 or val > 100:
                    continue
            elif api_key in ("cache_ttl", "ban_ttl"):
                val = int(val)
                if val < 60:
                    continue
            setattr(policy, model_key, val)
    policy.save()
    invalidate_policy_cache()
    return api_success(message=_("系统设置已更新"))


@csrf_protect
@api_permission_required("django_ip_safeguard.view_ipaccesslog")
@require_GET
def security_audit_log_view(request: HttpRequest) -> JsonResponse:
    page = _get_int_param(request, "page", 1)
    page_size = _get_int_param(request, "page_size", 20)
    action = str(request.GET.get("action", "")).strip()
    start_s = str(request.GET.get("start", "")).strip()
    end_s = str(request.GET.get("end", "")).strip()

    queryset = IpAccessLog.objects.filter(decision="security_audit").order_by("-created_at")
    if action:
        queryset = queryset.filter(reason__icontains=f"[{action}]")
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

    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    items = []
    for item in page_obj.object_list:
        reason = item.reason or ""
        action_type = ""
        detail = reason
        if reason.startswith("[") and "]" in reason:
            bracket_end = reason.index("]")
            action_type = reason[1:bracket_end]
            detail = reason[bracket_end + 1:].strip()
        items.append({
            "id": item.id,
            "action": action_type,
            "detail": detail,
            "ip": item.ip,
            "path": item.path,
            "created_at": item.created_at.isoformat(),
        })
    return api_success({
        "items": items,
        "pagination": {
            "page": page_obj.number,
            "page_size": page_size,
            "total": paginator.count,
            "num_pages": paginator.num_pages,
        },
    })


@csrf_protect
@api_permission_required("django_ip_safeguard.view_scheduledtask")
@require_http_methods(["GET", "POST"])
def scheduled_task_list_view(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        page = _get_int_param(request, "page", 1)
        page_size = _get_int_param(request, "page_size", 20)
        enabled = request.GET.get("enabled")
        task_type = str(request.GET.get("task_type", "")).strip()

        queryset = ScheduledTask.objects.all().order_by("-created_at")
        if enabled is not None:
            enabled_bool = enabled.lower() in ("true", "1", "yes")
            queryset = queryset.filter(enabled=enabled_bool)
        if task_type:
            queryset = queryset.filter(task_type=task_type)

        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        items = []
        for task in page_obj.object_list:
            items.append({
                "id": task.id,
                "name": task.name,
                "task_type": task.task_type,
                "task_type_display": task.get_task_type_display(),
                "command": task.command,
                "cron_expression": task.cron_expression,
                "cron_preset": task.cron_preset,
                "cron_preset_display": task.get_cron_preset_display(),
                "interval_minutes": task.interval_minutes,
                "schedule_display": task.get_schedule_display(),
                "enabled": task.enabled,
                "description": task.description,
                "last_run_at": task.last_run_at.isoformat() if task.last_run_at else None,
                "last_run_status": task.last_run_status,
                "last_run_output": task.last_run_output,
                "next_run_at": task.next_run_at.isoformat() if task.next_run_at else None,
                "run_count": task.run_count,
                "success_count": task.success_count,
                "failure_count": task.failure_count,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
            })
        return api_success({
            "items": items,
            "pagination": {
                "page": page_obj.number,
                "page_size": page_size,
                "total": paginator.count,
                "num_pages": paginator.num_pages,
            },
        })

    try:
        payload = _load_json_body(request)
    except json.JSONDecodeError:
        return api_error(_("JSON 格式错误"), code=4001, status=400)

    name = str(payload.get("name", "")).strip()
    if not name:
        return api_error(_("任务名称不能为空"), code=4001, status=400)

    if ScheduledTask.objects.filter(name=name).exists():
        return api_error(_("任务名称已存在"), code=4001, status=400)

    task_type = str(payload.get("task_type", "custom")).strip()
    cron_preset = str(payload.get("cron_preset", "@daily")).strip()
    cron_expression = str(payload.get("cron_expression", "")).strip()
    interval_minutes = _get_int_param(request, "interval_minutes", 0)
    enabled = payload.get("enabled", True)
    description = str(payload.get("description", "")).strip()
    command = str(payload.get("command", "")).strip()

    task = ScheduledTask.objects.create(
        name=name,
        task_type=task_type,
        command=command,
        cron_expression=cron_expression,
        cron_preset=cron_preset,
        interval_minutes=interval_minutes,
        enabled=enabled,
        description=description,
    )
    task.next_run_at = task.calculate_next_run()
    task.save(update_fields=["next_run_at"])

    return api_success({
        "id": task.id,
        "name": task.name,
        "next_run_at": task.next_run_at.isoformat() if task.next_run_at else None,
    }, message=_("定时任务已创建"))


@csrf_protect
@api_permission_required("django_ip_safeguard.change_scheduledtask")
@require_http_methods(["GET", "PUT", "DELETE"])
def scheduled_task_detail_view(request: HttpRequest, task_id: int) -> JsonResponse:
    try:
        task = ScheduledTask.objects.get(id=task_id)
    except ScheduledTask.DoesNotExist:
        return api_error(_("任务不存在"), code=4040, status=404)

    if request.method == "GET":
        return api_success({
            "id": task.id,
            "name": task.name,
            "task_type": task.task_type,
            "task_type_display": task.get_task_type_display(),
            "command": task.command,
            "cron_expression": task.cron_expression,
            "cron_preset": task.cron_preset,
            "cron_preset_display": task.get_cron_preset_display(),
            "interval_minutes": task.interval_minutes,
            "schedule_display": task.get_schedule_display(),
            "enabled": task.enabled,
            "description": task.description,
            "last_run_at": task.last_run_at.isoformat() if task.last_run_at else None,
            "last_run_status": task.last_run_status,
            "last_run_output": task.last_run_output,
            "next_run_at": task.next_run_at.isoformat() if task.next_run_at else None,
            "run_count": task.run_count,
            "success_count": task.success_count,
            "failure_count": task.failure_count,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
        })

    if request.method == "DELETE":
        task.delete()
        return api_success(message=_("定时任务已删除"))

    try:
        payload = _load_json_body(request)
    except json.JSONDecodeError:
        return api_error(_("JSON 格式错误"), code=4001, status=400)

    if "name" in payload:
        new_name = str(payload["name"]).strip()
        if new_name != task.name and ScheduledTask.objects.filter(name=new_name).exists():
            return api_error(_("任务名称已存在"), code=4001, status=400)
        task.name = new_name

    if "task_type" in payload:
        task.task_type = str(payload["task_type"]).strip()
    if "command" in payload:
        task.command = str(payload["command"]).strip()
    if "cron_expression" in payload:
        task.cron_expression = str(payload["cron_expression"]).strip()
    if "cron_preset" in payload:
        task.cron_preset = str(payload["cron_preset"]).strip()
    if "interval_minutes" in payload:
        task.interval_minutes = int(payload["interval_minutes"])
    if "enabled" in payload:
        task.enabled = bool(payload["enabled"])
    if "description" in payload:
        task.description = str(payload["description"]).strip()

    task.save()
    task.next_run_at = task.calculate_next_run()
    task.save(update_fields=["next_run_at"])

    return api_success({
        "id": task.id,
        "name": task.name,
        "next_run_at": task.next_run_at.isoformat() if task.next_run_at else None,
    }, message=_("定时任务已更新"))


@csrf_protect
@api_permission_required("django_ip_safeguard.change_scheduledtask")
@require_http_methods(["POST"])
def scheduled_task_run_view(request: HttpRequest, task_id: int) -> JsonResponse:
    try:
        task = ScheduledTask.objects.get(id=task_id)
    except ScheduledTask.DoesNotExist:
        return api_error(_("任务不存在"), code=4040, status=404)

    from django_ip_safeguard.services.task_scheduler import scheduler
    scheduler._execute_task_async(task)

    return api_success(message=_("任务已触发执行"))


@csrf_protect
@api_permission_required("auth.view_user")
@require_GET
def django_admin_group_list_view(request: HttpRequest) -> JsonResponse:
    """组列表，供系统用户管理表单多选。"""
    items = [{"id": g.id, "name": g.name} for g in Group.objects.order_by("name")]
    # 使用对象包装：api_success 内 `data or {}` 会把空列表当成假值
    return api_success({"items": items})


def _django_user_to_dict(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "email": u.email or "",
        "first_name": u.first_name or "",
        "last_name": u.last_name or "",
        "is_staff": u.is_staff,
        "is_superuser": u.is_superuser,
        "is_active": u.is_active,
        "last_login": u.last_login.isoformat() if u.last_login else None,
        "date_joined": u.date_joined.isoformat() if u.date_joined else None,
        "groups": [{"id": g.id, "name": g.name} for g in u.groups.all()],
    }


@csrf_protect
@require_http_methods(["GET", "POST"])
def django_admin_users_collection_view(request: HttpRequest) -> JsonResponse:
    """Django 系统用户列表（GET）与创建（POST），权限与 auth 应用一致。"""
    actor = _resolve_request_user(request)
    if not actor.is_authenticated:
        return api_error(_("未登录或登录已过期"), code=4010, status=401)
    if not actor.is_staff:
        return api_error(_("权限不足"), code=4030, status=403)

    if request.method == "GET":
        if not actor.has_perm("auth.view_user"):
            return api_error(_("权限不足：缺少操作权限"), code=4031, status=403)
        page = _get_int_param(request, "page", 1)
        page_size = _get_int_param(request, "page_size", 20, max_value=100)
        q = str(request.GET.get("q", "")).strip()
        qs = User.objects.prefetch_related("groups").all().order_by("-date_joined")
        if q:
            qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q))
        paginator = Paginator(qs, page_size)
        page_obj = paginator.get_page(page)
        items = [_django_user_to_dict(u) for u in page_obj.object_list]
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

    if not actor.has_perm("auth.add_user"):
        return api_error(_("权限不足：缺少操作权限"), code=4031, status=403)
    try:
        payload = _load_json_body(request)
    except json.JSONDecodeError:
        return api_error(_("JSON 格式错误"), code=4001, status=400)
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))
    email = str(payload.get("email", "")).strip()
    if not username:
        return api_error(_("用户名不能为空"), code=4002, status=400)
    if len(password) < 8:
        return api_error(_("密码长度至少 8 位"), code=4003, status=400)
    if User.objects.filter(username=username).exists():
        return api_error(_("用户名已存在"), code=4004, status=400)
    want_super = bool(payload.get("is_superuser", False))
    if want_super and not actor.is_superuser:
        return api_error(_("仅超级用户可创建超级用户账号"), code=4032, status=403)
    user = User.objects.create_user(username=username, email=email or "", password=password)
    user.is_staff = bool(payload.get("is_staff", False))
    user.is_superuser = want_super
    user.first_name = str(payload.get("first_name", "")).strip()[:150]
    user.last_name = str(payload.get("last_name", "")).strip()[:150]
    user.save()
    _log_security_audit(request, "django_user_create", f"actor={actor.username} new={username}", actor)
    user = User.objects.prefetch_related("groups").get(pk=user.pk)
    return api_success(_django_user_to_dict(user), message=_("用户已创建"))


@csrf_protect
@require_http_methods(["GET", "PATCH"])
def django_admin_user_detail_view(request: HttpRequest, user_id: int) -> JsonResponse:
    """单用户详情（GET）与部分更新（PATCH）。"""
    actor = _resolve_request_user(request)
    if not actor.is_authenticated:
        return api_error(_("未登录或登录已过期"), code=4010, status=401)
    if not actor.is_staff:
        return api_error(_("权限不足"), code=4030, status=403)
    try:
        target = User.objects.prefetch_related("groups").get(pk=user_id)
    except User.DoesNotExist:
        return api_error(_("用户不存在"), code=4040, status=404)

    if request.method == "GET":
        if not actor.has_perm("auth.view_user"):
            return api_error(_("权限不足：缺少操作权限"), code=4031, status=403)
        return api_success(_django_user_to_dict(target))

    if not actor.has_perm("auth.change_user"):
        return api_error(_("权限不足：缺少操作权限"), code=4031, status=403)
    if target.is_superuser and not actor.is_superuser:
        return api_error(_("不能修改超级用户账号"), code=4032, status=403)

    try:
        payload = _load_json_body(request)
    except json.JSONDecodeError:
        return api_error(_("JSON 格式错误"), code=4001, status=400)

    if "email" in payload:
        target.email = str(payload.get("email") or "").strip()[:254]
    if "first_name" in payload:
        target.first_name = str(payload.get("first_name") or "").strip()[:150]
    if "last_name" in payload:
        target.last_name = str(payload.get("last_name") or "").strip()[:150]

    if "is_active" in payload:
        new_active = bool(payload.get("is_active"))
        if target.pk == actor.pk and not new_active:
            return api_error(_("不能禁用当前登录账号"), code=4005, status=400)
        target.is_active = new_active

    if "is_staff" in payload:
        new_staff = bool(payload.get("is_staff"))
        if target.pk == actor.pk and not new_staff:
            return api_error(_("不能取消当前账号的 Staff 权限"), code=4006, status=400)
        target.is_staff = new_staff

    if "is_superuser" in payload:
        if not actor.is_superuser:
            return api_error(_("仅超级用户可修改超级用户标志"), code=4032, status=403)
        target.is_superuser = bool(payload.get("is_superuser"))

    if "group_ids" in payload:
        raw_ids = payload.get("group_ids")
        if not isinstance(raw_ids, list):
            return api_error(_("group_ids 须为数组"), code=4007, status=400)
        ids = []
        for x in raw_ids:
            try:
                ids.append(int(x))
            except (TypeError, ValueError):
                return api_error(_("group_ids 含非法 ID"), code=4008, status=400)
        groups = list(Group.objects.filter(pk__in=ids))
        if len(groups) != len(set(ids)):
            return api_error(_("存在无效的组 ID"), code=4009, status=400)
        target.groups.set(groups)

    pwd = payload.get("password")
    if pwd is not None and str(pwd) != "":
        if not actor.has_perm("auth.change_user"):
            return api_error(_("无权修改密码"), code=4031, status=403)
        if target.is_superuser and not actor.is_superuser:
            return api_error(_("不能修改超级用户密码"), code=4032, status=403)
        pwd_str = str(pwd)
        if len(pwd_str) < 8:
            return api_error(_("密码长度至少 8 位"), code=4003, status=400)
        target.set_password(pwd_str)

    target.save()
    _log_security_audit(
        request,
        "django_user_update",
        f"actor={actor.username} target={target.username} fields={list(payload.keys())}",
        actor,
    )
    target = User.objects.prefetch_related("groups").get(pk=target.pk)
    return api_success(_django_user_to_dict(target), message=_("用户已更新"))
