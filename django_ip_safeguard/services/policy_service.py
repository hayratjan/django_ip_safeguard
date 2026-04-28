"""策略中心运行时：加载多条策略并在请求级路由。

兼容性：
- 旧调用 ``load_effective_policy(base_config)`` 仍可工作；当 ``request`` 不传或没有非 default 策略时，
  返回与旧版本等价的合并配置（取 ``name="default"``）。
- 新调用 ``load_effective_policy(base_config, request=request)`` 会在多条策略里按 host/path/method 路由。
- 进程内字典缓存仍存在；同时通过 Redis pubsub 在多 worker 间失效。
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import replace
from typing import List

from django_ip_safeguard.conf import IpGuardSettings
from django_ip_safeguard.services.policy_router import CompiledPolicy, select_policy

logger = logging.getLogger(__name__)

_POLICY_CACHE: dict = {
    "policies": None,
    "expires_at": 0.0,
}
_SUBSCRIBER_STARTED = False
_SUBSCRIBER_LOCK = threading.Lock()

# 与策略中心、API 校验一致的地理池规则取值
GEO_POOL_RULE_CHOICES = frozenset({"off", "allow_only_in_pool", "block_in_pool"})

# 默认信号权重（策略未指定 signal_weights 时使用）
DEFAULT_SIGNAL_WEIGHTS = {
    "risk_score": 1.0,
    "tag_blocked": 50.0,
    "country_blocked": 60.0,
    "country_not_allowed": 60.0,
    "geo_pool": 30.0,
    "rate_limit_hit": 40.0,
    "reputation_rising": 20.0,
    "tor": 35.0,
    "datacenter": 15.0,
    "botnet": 70.0,
}


def _to_upper_tuple(value) -> tuple:
    if not value:
        return ()
    return tuple(str(v).upper() for v in value if str(v).strip())


def _to_str_tuple(value) -> tuple:
    if not value:
        return ()
    return tuple(str(v).strip() for v in value if str(v).strip())


def _normalize_geo_rule(value: str) -> str:
    v = str(value or "off").strip().lower()
    return v if v in GEO_POOL_RULE_CHOICES else "off"


def _compile_policy(policy) -> CompiledPolicy:
    """ORM 行 → CompiledPolicy（不可变快照）。"""
    return CompiledPolicy(
        name=str(policy.name or "default"),
        priority=int(getattr(policy, "priority", 10_000) or 10_000),
        enabled=bool(policy.enabled),
        match_host_regex=str(getattr(policy, "match_host_regex", "") or ""),
        match_path_prefixes=_to_str_tuple(getattr(policy, "match_path_prefixes", ())),
        match_methods=_to_str_tuple(getattr(policy, "match_methods", ())),
        raw={
            "enabled": bool(policy.enabled),
            "risk_score_threshold": int(policy.risk_score_threshold or 0),
            "blocked_risk_tags": _to_upper_tuple(policy.blocked_risk_tags),
            "allowed_countries": _to_upper_tuple(policy.allowed_countries),
            "blocked_countries": _to_upper_tuple(policy.blocked_countries),
            "ip_whitelist": _to_str_tuple(policy.ip_whitelist),
            "ip_blacklist": _to_str_tuple(policy.ip_blacklist),
            "rate_limit_per_minute": int(policy.rate_limit_per_minute or 0),
            "fail_open": bool(policy.fail_open),
            "fail_open_path_prefixes": _to_str_tuple(policy.fail_open_path_prefixes),
            "fail_close_path_prefixes": _to_str_tuple(policy.fail_close_path_prefixes),
            "block_status_code": int(policy.block_status_code or 403),
            "challenge_status_code": int(getattr(policy, "challenge_status_code", policy.block_status_code or 403) or 403),
            "cache_ttl": int(policy.cache_ttl or 3600),
            "ban_ttl": int(policy.ban_ttl or 86400),
            "use_db_log": bool(policy.use_db_log),
            "china_pool_rule": _normalize_geo_rule(getattr(policy, "china_pool_rule", "off")),
            "international_pool_rule": _normalize_geo_rule(getattr(policy, "international_pool_rule", "off")),
            "tier_thresholds": dict(getattr(policy, "tier_thresholds", {}) or {}),
            "signal_weights": dict(getattr(policy, "signal_weights", {}) or {}),
            "medium_action": str(getattr(policy, "medium_action", "block") or "block"),
            "high_action": str(getattr(policy, "high_action", "ban") or "ban"),
            "policy_name": str(policy.name or "default"),
            "policy_priority": int(getattr(policy, "priority", 10_000) or 10_000),
            "match_host_regex": str(getattr(policy, "match_host_regex", "") or ""),
            "match_path_prefixes": _to_str_tuple(getattr(policy, "match_path_prefixes", ())),
            "match_methods": _to_str_tuple(getattr(policy, "match_methods", ())),
        },
    )


def _merge_into_config(base_config: IpGuardSettings, compiled: CompiledPolicy) -> IpGuardSettings:
    """把 CompiledPolicy.raw 合并回 IpGuardSettings；补齐之前遗漏的字段。"""
    raw = compiled.raw
    medium = raw["tier_thresholds"].get("medium")
    high = raw["tier_thresholds"].get("high")
    return replace(
        base_config,
        enabled=raw["enabled"],
        risk_score_threshold=raw["risk_score_threshold"],
        blocked_risk_tags=raw["blocked_risk_tags"],
        allowed_countries=raw["allowed_countries"],
        blocked_countries=raw["blocked_countries"],
        ip_whitelist=raw["ip_whitelist"],
        ip_blacklist=raw["ip_blacklist"],
        rate_limit_per_minute=raw["rate_limit_per_minute"],
        fail_open=raw["fail_open"],
        fail_open_path_prefixes=raw["fail_open_path_prefixes"],
        fail_close_path_prefixes=raw["fail_close_path_prefixes"],
        block_status_code=raw["block_status_code"],
        challenge_status_code=raw["challenge_status_code"],
        cache_ttl=raw["cache_ttl"],
        ban_ttl=raw["ban_ttl"],
        use_db_log=raw["use_db_log"],
        china_pool_rule=raw["china_pool_rule"],
        international_pool_rule=raw["international_pool_rule"],
        signal_weights=raw["signal_weights"] or dict(DEFAULT_SIGNAL_WEIGHTS),
        medium_action=raw["medium_action"],
        high_action=raw["high_action"],
        tier_medium=int(medium) if isinstance(medium, (int, float)) else base_config.tier_medium,
        tier_high=int(high) if isinstance(high, (int, float)) else raw["risk_score_threshold"],
        policy_name=raw["policy_name"],
        policy_priority=raw["policy_priority"],
        match_host_regex=raw["match_host_regex"],
        match_path_prefixes=raw["match_path_prefixes"],
        match_methods=raw["match_methods"],
    )


def _load_compiled_policies(base_config: IpGuardSettings) -> List[CompiledPolicy]:
    """从数据库加载所有策略并编译；带进程内短缓存。"""
    now = time.time()
    if _POLICY_CACHE["policies"] is not None and now < _POLICY_CACHE["expires_at"]:
        return _POLICY_CACHE["policies"]

    try:
        from django_ip_safeguard.models import IpGuardPolicy

        rows = list(IpGuardPolicy.objects.all())
        compiled = [_compile_policy(p) for p in rows]
    except Exception:  # noqa: BLE001
        # 策略中心异常时回退默认配置，避免影响主流程可用性
        compiled = []

    _POLICY_CACHE["policies"] = compiled
    _POLICY_CACHE["expires_at"] = now + max(1, base_config.policy_cache_seconds)
    return compiled


def _request_match_args(request) -> tuple:
    """从 Django request 中提取 (host, path, method)。"""
    if request is None:
        return ("", "", "")
    try:
        host = request.get_host().split(":", 1)[0]
    except Exception:  # noqa: BLE001
        host = ""
    return (host, getattr(request, "path", "") or "", getattr(request, "method", "") or "")


def load_effective_policy(base_config: IpGuardSettings, request=None) -> IpGuardSettings:
    """读取企业策略中心配置；按 request 路由后并入 base_config。

    优先级：路由命中策略 > name="default" 策略 > base_config 默认。
    """

    if not base_config.enable_policy_center:
        return base_config

    compiled = _load_compiled_policies(base_config)
    if not compiled:
        return base_config

    host, path, method = _request_match_args(request)
    selected = select_policy(compiled, host=host, path=path, method=method)
    if selected is None:
        # 未命中时优先用 name="default" 兜底
        selected = next((p for p in compiled if p.name == "default"), None)
    if selected is None:
        return base_config

    return _merge_into_config(base_config, selected)


def invalidate_policy_cache(broadcast: bool = True) -> None:
    """清除本进程缓存；可选广播给其它 worker。"""
    _POLICY_CACHE["policies"] = None
    _POLICY_CACHE["expires_at"] = 0.0
    if not broadcast:
        return
    try:
        from django_ip_safeguard.conf import get_settings
        from django_ip_safeguard.services.cache import RedisCacheService
        cache = RedisCacheService(get_settings().redis_url)
        cache.publish_policy_invalidate()
    except Exception:  # noqa: BLE001
        return None


def start_policy_invalidate_subscriber(redis_url: str) -> None:
    """在中间件 ``__init__`` 调用一次；后台线程订阅 Redis 通道清本地缓存。

    设计为 best-effort：Redis 不可用时静默退出，不影响请求处理。
    """
    global _SUBSCRIBER_STARTED
    with _SUBSCRIBER_LOCK:
        if _SUBSCRIBER_STARTED:
            return
        _SUBSCRIBER_STARTED = True

    def _run():
        try:
            from django_ip_safeguard.services.cache import POLICY_INVALIDATE_CHANNEL, RedisCacheService
            cache = RedisCacheService(redis_url)
            pubsub = cache.pubsub()
            pubsub.subscribe(POLICY_INVALIDATE_CHANNEL)
            for _msg in pubsub.listen():
                # 收到任意消息（含订阅确认）都安全清缓存：开销小、无副作用
                _POLICY_CACHE["policies"] = None
                _POLICY_CACHE["expires_at"] = 0.0
        except Exception as exc:  # noqa: BLE001
            logger.warning("策略失效订阅线程退出: %s", exc)

    t = threading.Thread(target=_run, name="ip-guard-policy-invalidate", daemon=True)
    t.start()
