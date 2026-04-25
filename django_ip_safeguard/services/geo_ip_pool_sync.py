"""从远程拉取 CIDR 文本并写入 Redis，同时更新 IpGeoPoolStatus。"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx
from django.utils import timezone

from django_ip_safeguard.conf import IpGuardSettings
from django_ip_safeguard.models import IpGeoPoolStatus
from django_ip_safeguard.services.cache import RedisCacheService
from django_ip_safeguard.services.geo_ip_pool_index import build_index_from_text
from django_ip_safeguard.services.geo_ip_pool_runtime import invalidate_local_geo_pool_cache

logger = logging.getLogger(__name__)

POOL_CHINA = "china"
POOL_INTERNATIONAL = "international"


def _fetch_text(url: str, timeout: float) -> str:
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text


def sync_geo_pool(
    pool_key: str,
    url: str,
    cfg: IpGuardSettings,
    *,
    timeout: float = 120.0,
) -> Dict[str, Any]:
    """
    同步单个池：拉取 URL、构建索引、写入 Redis、更新数据库状态。
    返回 { ok, pool_key, line_count, error? }
    """

    if not url.strip():
        msg = "未配置数据源 URL，跳过"
        IpGeoPoolStatus.objects.update_or_create(
            pool_key=pool_key,
            defaults={
                "source_url": "",
                "last_error": msg,
            },
        )
        return {"ok": False, "pool_key": pool_key, "line_count": 0, "error": msg}

    cache = RedisCacheService(cfg.redis_url)
    try:
        text = _fetch_text(url, timeout=timeout)
        index = build_index_from_text(text)
        index["pool_key"] = pool_key
        cache.set_geo_pool_data(pool_key, index)
        invalidate_local_geo_pool_cache()
        v4c = len(index.get("v4_intervals") or [])
        v6c = len(index.get("v6_nets") or [])
        IpGeoPoolStatus.objects.update_or_create(
            pool_key=pool_key,
            defaults={
                "source_url": url[:512],
                "line_count": int(index.get("line_count") or 0),
                "v4_interval_count": v4c,
                "v6_net_count": v6c,
                "last_ok_at": timezone.now(),
                "last_error": "",
            },
        )
        logger.info("地理 IP 池同步成功: %s 行数=%s v4区间=%s v6=%s", pool_key, index.get("line_count"), v4c, v6c)
        return {
            "ok": True,
            "pool_key": pool_key,
            "line_count": int(index.get("line_count") or 0),
            "v4_interval_count": v4c,
            "v6_net_count": v6c,
        }
    except Exception as exc:  # noqa: BLE001
        err = str(exc)
        logger.exception("地理 IP 池同步失败: %s", pool_key)
        IpGeoPoolStatus.objects.update_or_create(
            pool_key=pool_key,
            defaults={
                "source_url": url[:512],
                "last_error": err[:2000],
            },
        )
        return {"ok": False, "pool_key": pool_key, "line_count": 0, "error": err}


def sync_all_geo_pools(cfg: IpGuardSettings) -> Dict[str, Any]:
    """按配置同步中国内池与国际池（国际池 URL 为空则跳过）。"""

    results = []
    results.append(sync_geo_pool(POOL_CHINA, cfg.geo_china_pool_url, cfg))
    if cfg.geo_international_pool_url.strip():
        results.append(sync_geo_pool(POOL_INTERNATIONAL, cfg.geo_international_pool_url, cfg))
    else:
        results.append(
            {
                "ok": False,
                "pool_key": POOL_INTERNATIONAL,
                "line_count": 0,
                "error": "IP_GUARD_GEO_INTERNATIONAL_POOL_URL 未配置，跳过国际池",
            }
        )
    return {"results": results}
