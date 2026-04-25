import os
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
    ip_whitelist: Tuple[str, ...] = ()
    ip_blacklist: Tuple[str, ...] = ()
    rate_limit_per_minute: int = 0
    fail_open: bool = True
    fail_open_path_prefixes: Tuple[str, ...] = ()
    fail_close_path_prefixes: Tuple[str, ...] = ()
    block_status_code: int = 403
    trusted_proxy_cidrs: Tuple[str, ...] = ()
    use_db_log: bool = False
    enable_policy_center: bool = True
    policy_cache_seconds: int = 30
    ip_mask_enabled: bool = True
    ip_mask_keep_prefix: int = 2
    provider_circuit_breaker_failures: int = 5
    provider_circuit_breaker_ttl: int = 60
    high_risk_cache_ttl: int = 7200
    low_risk_cache_ttl: int = 1800
    dedupe_lock_seconds: int = 3
    admin_url_prefix: str = "ip-guard"
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_token_ttl_seconds: int = 7200
    jwt_refresh_token_ttl_seconds: int = 604800
    china_pool_rule: str = "off"
    international_pool_rule: str = "off"
    geo_china_pool_url: str = "https://raw.githubusercontent.com/17mon/china_ip_list/master/china_ip_list.txt"
    geo_international_pool_url: str = ""
    geo_pool_index_cache_seconds: int = 60

    # GeoIP2 本地数据库
    geoip2_city_db_path: str = ""
    geoip2_asn_db_path: str = ""
    geoip2_enabled: bool = False

    # 多 Provider 降级链
    provider_chain_enabled: bool = False
    provider_chain_names: Tuple[str, ...] = ()

    # 分层缓存
    l1_cache_enabled: bool = True
    l1_cache_ttl: float = 10.0
    l1_cache_max_size: int = 10000

    # 本地风险规则引擎
    local_risk_engine_enabled: bool = True
    local_risk_subnet_attack_threshold: int = 10

    # 威胁情报订阅
    threat_intel_enabled: bool = False
    threat_intel_spamhaus_enabled: bool = True
    threat_intel_tor_enabled: bool = True
    threat_intel_emerging_enabled: bool = True
    threat_intel_custom_feeds: str = ""

    # IP 关联分析
    ip_correlation_enabled: bool = True

    # IP 信誉历史
    ip_reputation_enabled: bool = True
    ip_reputation_snapshot_interval: int = 3600

    # CIDR 多源备份
    geo_pool_multi_source_enabled: bool = True
    geo_china_pool_backup_urls: Tuple[str, ...] = ()
    geo_international_pool_backup_urls: Tuple[str, ...] = ()


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


def _read_jwt_secret_key() -> str:
    return str(
        getattr(
            settings,
            "IP_GUARD_JWT_SECRET_KEY",
            os.getenv("IP_GUARD_JWT_SECRET_KEY", ""),
        )
    ).strip()


def get_settings() -> IpGuardSettings:
    return IpGuardSettings(
        enabled=getattr(settings, "IP_GUARD_ENABLED", True),
        redis_url=getattr(settings, "IP_GUARD_REDIS_URL", "redis://127.0.0.1:6379/0"),
        cache_ttl=getattr(settings, "IP_GUARD_CACHE_TTL", 3600),
        ban_ttl=getattr(settings, "IP_GUARD_BAN_TTL", 86400),
        provider=getattr(settings, "IP_GUARD_PROVIDER", "dummy"),
        provider_endpoint=getattr(settings, "IP_GUARD_PROVIDER_ENDPOINT", ""),
        provider_api_key=getattr(
            settings,
            "IP_GUARD_PROVIDER_API_KEY",
            os.getenv("IP_GUARD_PROVIDER_API_KEY", ""),
        ),
        provider_timeout=float(getattr(settings, "IP_GUARD_PROVIDER_TIMEOUT", 3.0)),
        provider_max_retries=int(getattr(settings, "IP_GUARD_PROVIDER_MAX_RETRIES", 2)),
        provider_retry_backoff=float(getattr(settings, "IP_GUARD_PROVIDER_RETRY_BACKOFF", 0.2)),
        provider_headers=getattr(settings, "IP_GUARD_PROVIDER_HEADERS", {}) or {},
        risk_score_threshold=getattr(settings, "IP_GUARD_RISK_SCORE_THRESHOLD", 70),
        blocked_countries=_to_tuple(getattr(settings, "IP_GUARD_BLOCKED_COUNTRIES", ())),
        allowed_countries=_to_tuple(getattr(settings, "IP_GUARD_ALLOWED_COUNTRIES", ())),
        blocked_risk_tags=_to_tuple(getattr(settings, "IP_GUARD_BLOCKED_RISK_TAGS", ("tor", "proxy", "vpn"))),
        ip_whitelist=_to_str_tuple(getattr(settings, "IP_GUARD_IP_WHITELIST", ())),
        ip_blacklist=_to_str_tuple(getattr(settings, "IP_GUARD_IP_BLACKLIST", ())),
        rate_limit_per_minute=int(getattr(settings, "IP_GUARD_RATE_LIMIT_PER_MINUTE", 0)),
        fail_open=getattr(settings, "IP_GUARD_FAIL_OPEN", True),
        fail_open_path_prefixes=_to_str_tuple(getattr(settings, "IP_GUARD_FAIL_OPEN_PATH_PREFIXES", ())),
        fail_close_path_prefixes=_to_str_tuple(getattr(settings, "IP_GUARD_FAIL_CLOSE_PATH_PREFIXES", ())),
        block_status_code=getattr(settings, "IP_GUARD_BLOCK_STATUS_CODE", 403),
        trusted_proxy_cidrs=tuple(
            getattr(settings, "IP_GUARD_TRUSTED_PROXY_CIDRS", ())
        ),
        use_db_log=getattr(settings, "IP_GUARD_USE_DB_LOG", False),
        enable_policy_center=getattr(settings, "IP_GUARD_ENABLE_POLICY_CENTER", True),
        policy_cache_seconds=int(getattr(settings, "IP_GUARD_POLICY_CACHE_SECONDS", 30)),
        ip_mask_enabled=bool(getattr(settings, "IP_GUARD_IP_MASK_ENABLED", True)),
        ip_mask_keep_prefix=int(getattr(settings, "IP_GUARD_IP_MASK_KEEP_PREFIX", 2)),
        provider_circuit_breaker_failures=int(
            getattr(settings, "IP_GUARD_PROVIDER_CIRCUIT_BREAKER_FAILURES", 5)
        ),
        provider_circuit_breaker_ttl=int(
            getattr(settings, "IP_GUARD_PROVIDER_CIRCUIT_BREAKER_TTL", 60)
        ),
        high_risk_cache_ttl=int(getattr(settings, "IP_GUARD_HIGH_RISK_CACHE_TTL", 7200)),
        low_risk_cache_ttl=int(getattr(settings, "IP_GUARD_LOW_RISK_CACHE_TTL", 1800)),
        dedupe_lock_seconds=int(getattr(settings, "IP_GUARD_DEDUPE_LOCK_SECONDS", 3)),
        admin_url_prefix=str(getattr(settings, "IP_GUARD_ADMIN_URL_PREFIX", "ip-guard")).strip("/"),
        jwt_secret_key=_read_jwt_secret_key(),
        jwt_algorithm=str(getattr(settings, "IP_GUARD_JWT_ALGORITHM", "HS256")),
        jwt_access_token_ttl_seconds=int(getattr(settings, "IP_GUARD_JWT_ACCESS_TTL", 7200)),
        jwt_refresh_token_ttl_seconds=int(getattr(settings, "IP_GUARD_JWT_REFRESH_TTL", 604800)),
        china_pool_rule=str(getattr(settings, "IP_GUARD_CHINA_POOL_RULE", "off")).strip().lower()
        or "off",
        international_pool_rule=str(
            getattr(settings, "IP_GUARD_INTERNATIONAL_POOL_RULE", "off")
        ).strip().lower()
        or "off",
        geo_china_pool_url=str(
            getattr(
                settings,
                "IP_GUARD_GEO_CHINA_POOL_URL",
                "https://raw.githubusercontent.com/17mon/china_ip_list/master/china_ip_list.txt",
            )
        ).strip(),
        geo_international_pool_url=str(
            getattr(settings, "IP_GUARD_GEO_INTERNATIONAL_POOL_URL", "")
        ).strip(),
        geo_pool_index_cache_seconds=int(
            getattr(settings, "IP_GUARD_GEO_POOL_INDEX_CACHE_SECONDS", 60)
        ),
        geoip2_city_db_path=str(
            getattr(settings, "IP_GUARD_GEOIP2_CITY_DB_PATH", "")
        ).strip(),
        geoip2_asn_db_path=str(
            getattr(settings, "IP_GUARD_GEOIP2_ASN_DB_PATH", "")
        ).strip(),
        geoip2_enabled=bool(getattr(settings, "IP_GUARD_GEOIP2_ENABLED", False)),
        provider_chain_enabled=bool(getattr(settings, "IP_GUARD_PROVIDER_CHAIN_ENABLED", False)),
        provider_chain_names=_to_str_tuple(
            getattr(settings, "IP_GUARD_PROVIDER_CHAIN_NAMES", ())
        ),
        l1_cache_enabled=bool(getattr(settings, "IP_GUARD_L1_CACHE_ENABLED", True)),
        l1_cache_ttl=float(getattr(settings, "IP_GUARD_L1_CACHE_TTL", 10.0)),
        l1_cache_max_size=int(getattr(settings, "IP_GUARD_L1_CACHE_MAX_SIZE", 10000)),
        local_risk_engine_enabled=bool(getattr(settings, "IP_GUARD_LOCAL_RISK_ENGINE_ENABLED", True)),
        local_risk_subnet_attack_threshold=int(
            getattr(settings, "IP_GUARD_LOCAL_RISK_SUBNET_ATTACK_THRESHOLD", 10)
        ),
        threat_intel_enabled=bool(getattr(settings, "IP_GUARD_THREAT_INTEL_ENABLED", False)),
        threat_intel_spamhaus_enabled=bool(getattr(settings, "IP_GUARD_THREAT_INTEL_SPAMHAUS_ENABLED", True)),
        threat_intel_tor_enabled=bool(getattr(settings, "IP_GUARD_THREAT_INTEL_TOR_ENABLED", True)),
        threat_intel_emerging_enabled=bool(getattr(settings, "IP_GUARD_THREAT_INTEL_EMERGING_ENABLED", True)),
        threat_intel_custom_feeds=str(
            getattr(settings, "IP_GUARD_THREAT_INTEL_CUSTOM_FEEDS", "")
        ).strip(),
        ip_correlation_enabled=bool(getattr(settings, "IP_GUARD_IP_CORRELATION_ENABLED", True)),
        ip_reputation_enabled=bool(getattr(settings, "IP_GUARD_IP_REPUTATION_ENABLED", True)),
        ip_reputation_snapshot_interval=int(
            getattr(settings, "IP_GUARD_IP_REPUTATION_SNAPSHOT_INTERVAL", 3600)
        ),
        geo_pool_multi_source_enabled=bool(getattr(settings, "IP_GUARD_GEO_POOL_MULTI_SOURCE_ENABLED", True)),
        geo_china_pool_backup_urls=_to_str_tuple(
            getattr(settings, "IP_GUARD_GEO_CHINA_POOL_BACKUP_URLS", ())
        ),
        geo_international_pool_backup_urls=_to_str_tuple(
            getattr(settings, "IP_GUARD_GEO_INTERNATIONAL_POOL_BACKUP_URLS", ())
        ),
    )
