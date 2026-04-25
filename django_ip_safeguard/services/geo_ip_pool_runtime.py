"""地理 IP 池运行时：从 Redis 加载索引（带进程内短缓存），并据策略判定是否拦截。"""

from __future__ import annotations

import json
import time
from typing import Dict, Optional, Tuple

from django_ip_safeguard.conf import IpGuardSettings
from django_ip_safeguard.services.cache import RedisCacheService
from django_ip_safeguard.services.geo_ip_pool_index import index_has_cidr_data, ip_matches_index

# 进程内缓存：(pool_key -> (过期时间戳, 解析后的 dict))
_POOL_CACHE: Dict[str, Tuple[float, Optional[dict]]] = {}


def _cache_ttl_seconds(cfg: IpGuardSettings) -> float:
    return max(5.0, float(cfg.geo_pool_index_cache_seconds))


def get_pool_payload(
    cache: RedisCacheService, pool_key: str, cfg: IpGuardSettings
) -> Optional[dict]:
    """读取单个池的索引 JSON；带本地缓存减轻 Redis 压力。"""

    now = time.time()
    exp = _cache_ttl_seconds(cfg)
    hit = _POOL_CACHE.get(pool_key)
    if hit and now < hit[0]:
        return hit[1]
    raw = cache.get_geo_pool_data(pool_key)
    if not raw:
        _POOL_CACHE[pool_key] = (now + exp, None)
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        _POOL_CACHE[pool_key] = (now + exp, None)
        return None
    _POOL_CACHE[pool_key] = (now + exp, data)
    return data


def invalidate_local_geo_pool_cache() -> None:
    """同步写入 Redis 后调用，避免多进程间仍需等待 TTL。"""

    _POOL_CACHE.clear()


def infer_country_from_pools(
    client_ip: str, cfg: IpGuardSettings, cache: RedisCacheService
) -> Optional[str]:
    """基于地理 IP 池推断国家码。命中中国池返回 'CN'，否则返回 None。"""

    china_payload = get_pool_payload(cache, "china", cfg)
    if index_has_cidr_data(china_payload) and ip_matches_index(client_ip, china_payload):
        return "CN"
    return None


def evaluate_geo_ip_pool_rules(
    client_ip: str, cfg: IpGuardSettings, cache: RedisCacheService
) -> Optional[str]:
    """
    在中国内 / 国际池规则下判断是否拦截。
    若池尚未同步（无有效 CIDR 数据），则不生效，避免误伤全站。
    """

    checks = (
        ("china", cfg.china_pool_rule, "中国内网段池"),
        ("international", cfg.international_pool_rule, "国际网段池"),
    )
    for pool_key, rule, label in checks:
        if rule == "off":
            continue
        payload = get_pool_payload(cache, pool_key, cfg)
        if not index_has_cidr_data(payload):
            continue
        inside = ip_matches_index(client_ip, payload)
        if rule == "allow_only_in_pool" and not inside:
            return f"未命中{label}（策略：仅允许池内访问）"
        if rule == "block_in_pool" and inside:
            return f"命中{label}（策略：禁止池内访问）"
    return None
