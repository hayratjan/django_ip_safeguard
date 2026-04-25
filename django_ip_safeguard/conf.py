from dataclasses import dataclass, field
from typing import Mapping, Optional, Tuple

from django.conf import settings


@dataclass(frozen=True)
class IpGuardSettings:
    """插件配置，统一从 Django settings 读取。"""

    enabled: bool = True
    redis_url: str = "redis://127.0.0.1:6379/0"
    cache_ttl: int = 3600
    ban_ttl: int = 86400
    provider: str = "dummy"
    provider_endpoint: str = ""
    provider_api_key: str = ""
    provider_timeout: float = 3.0
    provider_max_retries: int = 2
    provider_retry_backoff: float = 0.2
    provider_headers: Mapping[str, str] = field(default_factory=dict)
    risk_score_threshold: int = 70
    blocked_countries: Tuple[str, ...] = ()
    allowed_countries: Tuple[str, ...] = ()
    blocked_risk_tags: Tuple[str, ...] = ("tor", "proxy", "vpn")
    fail_open: bool = True
    fail_open_path_prefixes: Tuple[str, ...] = ()
    fail_close_path_prefixes: Tuple[str, ...] = ()
    block_status_code: int = 403
    trusted_proxy_cidrs: Tuple[str, ...] = ()
    use_db_log: bool = False


def _to_tuple(value: Optional[object]) -> Tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (tuple, list, set)):
        return tuple(str(v).upper() for v in value if str(v).strip())
    return (str(value).upper(),)


def _to_str_tuple(value: Optional[object]) -> Tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (tuple, list, set)):
        return tuple(str(v).strip() for v in value if str(v).strip())
    return (str(value).strip(),)


def get_settings() -> IpGuardSettings:
    """读取并构造插件配置对象。"""

    return IpGuardSettings(
        enabled=getattr(settings, "IP_GUARD_ENABLED", True),
        redis_url=getattr(settings, "IP_GUARD_REDIS_URL", "redis://127.0.0.1:6379/0"),
        cache_ttl=getattr(settings, "IP_GUARD_CACHE_TTL", 3600),
        ban_ttl=getattr(settings, "IP_GUARD_BAN_TTL", 86400),
        provider=getattr(settings, "IP_GUARD_PROVIDER", "dummy"),
        provider_endpoint=getattr(settings, "IP_GUARD_PROVIDER_ENDPOINT", ""),
        provider_api_key=getattr(settings, "IP_GUARD_PROVIDER_API_KEY", ""),
        provider_timeout=float(getattr(settings, "IP_GUARD_PROVIDER_TIMEOUT", 3.0)),
        provider_max_retries=int(getattr(settings, "IP_GUARD_PROVIDER_MAX_RETRIES", 2)),
        provider_retry_backoff=float(getattr(settings, "IP_GUARD_PROVIDER_RETRY_BACKOFF", 0.2)),
        provider_headers=getattr(settings, "IP_GUARD_PROVIDER_HEADERS", {}) or {},
        risk_score_threshold=getattr(settings, "IP_GUARD_RISK_SCORE_THRESHOLD", 70),
        blocked_countries=_to_tuple(getattr(settings, "IP_GUARD_BLOCKED_COUNTRIES", ())),
        allowed_countries=_to_tuple(getattr(settings, "IP_GUARD_ALLOWED_COUNTRIES", ())),
        blocked_risk_tags=_to_tuple(getattr(settings, "IP_GUARD_BLOCKED_RISK_TAGS", ("tor", "proxy", "vpn"))),
        fail_open=getattr(settings, "IP_GUARD_FAIL_OPEN", True),
        fail_open_path_prefixes=_to_str_tuple(getattr(settings, "IP_GUARD_FAIL_OPEN_PATH_PREFIXES", ())),
        fail_close_path_prefixes=_to_str_tuple(getattr(settings, "IP_GUARD_FAIL_CLOSE_PATH_PREFIXES", ())),
        block_status_code=getattr(settings, "IP_GUARD_BLOCK_STATUS_CODE", 403),
        trusted_proxy_cidrs=tuple(
            getattr(settings, "IP_GUARD_TRUSTED_PROXY_CIDRS", ())
        ),
        use_db_log=getattr(settings, "IP_GUARD_USE_DB_LOG", False),
    )
