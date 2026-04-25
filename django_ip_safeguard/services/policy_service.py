import time
from dataclasses import replace

from django_ip_safeguard.conf import IpGuardSettings

_POLICY_CACHE = {"data": None, "expires_at": 0.0}

# 与策略中心、API 校验一致的地理池规则取值
GEO_POOL_RULE_CHOICES = frozenset({"off", "allow_only_in_pool", "block_in_pool"})


def _to_upper_tuple(value) -> tuple:
    if not value:
        return ()
    return tuple(str(v).upper() for v in value if str(v).strip())


def _to_str_tuple(value) -> tuple:
    if not value:
        return ()
    return tuple(str(v).strip() for v in value if str(v).strip())


def load_effective_policy(base_config: IpGuardSettings) -> IpGuardSettings:
    """
    读取企业策略中心配置，优先级：数据库策略 > settings 默认配置。
    使用进程内短缓存减少每次请求都查库。
    """

    if not base_config.enable_policy_center:
        return base_config

    now = time.time()
    if _POLICY_CACHE["data"] is not None and now < _POLICY_CACHE["expires_at"]:
        return _POLICY_CACHE["data"]

    try:
        from django_ip_safeguard.models import IpGuardPolicy

        policy = IpGuardPolicy.objects.filter(name="default").first()
        if not policy:
            _POLICY_CACHE["data"] = base_config
            _POLICY_CACHE["expires_at"] = now + base_config.policy_cache_seconds
            return base_config

        china_rule = str(getattr(policy, "china_pool_rule", "off") or "off").strip().lower()
        intl_rule = str(getattr(policy, "international_pool_rule", "off") or "off").strip().lower()
        merged = replace(
            base_config,
            enabled=policy.enabled,
            risk_score_threshold=policy.risk_score_threshold,
            blocked_risk_tags=_to_upper_tuple(policy.blocked_risk_tags),
            allowed_countries=_to_upper_tuple(policy.allowed_countries),
            blocked_countries=_to_upper_tuple(policy.blocked_countries),
            ip_whitelist=_to_str_tuple(policy.ip_whitelist),
            ip_blacklist=_to_str_tuple(policy.ip_blacklist),
            rate_limit_per_minute=int(policy.rate_limit_per_minute or 0),
            fail_open=policy.fail_open,
            fail_open_path_prefixes=_to_str_tuple(policy.fail_open_path_prefixes),
            fail_close_path_prefixes=_to_str_tuple(policy.fail_close_path_prefixes),
            block_status_code=policy.block_status_code,
            cache_ttl=policy.cache_ttl,
            ban_ttl=policy.ban_ttl,
            use_db_log=policy.use_db_log,
            china_pool_rule=china_rule if china_rule in GEO_POOL_RULE_CHOICES else "off",
            international_pool_rule=intl_rule if intl_rule in GEO_POOL_RULE_CHOICES else "off",
        )
        _POLICY_CACHE["data"] = merged
        _POLICY_CACHE["expires_at"] = now + base_config.policy_cache_seconds
        return merged
    except Exception:  # noqa: BLE001
        # 策略中心异常时回退默认配置，避免影响主流程可用性。
        _POLICY_CACHE["data"] = base_config
        _POLICY_CACHE["expires_at"] = now + base_config.policy_cache_seconds
        return base_config


def invalidate_policy_cache() -> None:
    """用于策略变更后手动刷新缓存。"""

    _POLICY_CACHE["data"] = None
    _POLICY_CACHE["expires_at"] = 0.0
