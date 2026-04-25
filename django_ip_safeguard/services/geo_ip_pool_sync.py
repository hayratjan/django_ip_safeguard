"""从远程拉取 CIDR 文本并写入 Redis，同时更新 IpGeoPoolStatus。"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from urllib.parse import urlparse

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


class SsrfError(Exception):
    """SSRF 防护拦截异常。"""


MAX_SYNC_TIMEOUT = 120.0
MAX_REDIRECTS = 3


def _validate_url(url: str) -> None:
    """校验 URL 协议与主机，防止 SSRF 攻击。"""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise SsrfError(f"不支持的 URL 协议: {parsed.scheme}")
    if not parsed.netloc:
        raise SsrfError("URL 缺少主机名")
    # 禁止访问内网地址（基础防护）
    hostname = parsed.hostname or ""
    if hostname.startswith(("127.", "10.", "192.168.", "172.")):
        # 允许特定内网数据源可配置白名单，此处默认拦截
        raise SsrfError(f"禁止访问内网地址: {hostname}")
    if hostname in {"localhost", "0.0.0.0", "::1"}:
        raise SsrfError(f"禁止访问本地地址: {hostname}")


def _fetch_text(url: str, timeout: float) -> str:
    _validate_url(url)
    effective_timeout = min(float(timeout), MAX_SYNC_TIMEOUT)
    with httpx.Client(
        timeout=effective_timeout,
        follow_redirects=True,
        limits=httpx.Limits(max_redirects=MAX_REDIRECTS),
    ) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text


def sync_geo_pool(
    pool_key: str,
    url: str,
    cfg: IpGuardSettings,
    *,
    timeout: float = 60.0,
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
    """按配置同步中国内池与国际池（国际池 URL 为空则跳过且不覆盖 Redis 已有数据）。"""

    results = []
    results.append(sync_geo_pool(POOL_CHINA, cfg.geo_china_pool_url, cfg))
    intl_url = cfg.geo_international_pool_url.strip()
    if intl_url:
        results.append(sync_geo_pool(POOL_INTERNATIONAL, intl_url, cfg))
    else:
        results.append(
            {
                "ok": False,
                "pool_key": POOL_INTERNATIONAL,
                "skipped": True,
                "message": "未配置 IP_GUARD_GEO_INTERNATIONAL_POOL_URL，已跳过国际池同步",
            }
        )
    return {"results": results}
