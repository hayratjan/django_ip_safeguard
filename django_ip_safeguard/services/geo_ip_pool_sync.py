"""从远程拉取 CIDR 文本并写入 Redis，同时更新 IpGeoPoolStatus。支持多数据源备份与自动切换。"""

from __future__ import annotations

import logging
from typing import Any, Dict, List
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

CHINA_POOL_BACKUP_URLS = [
    "https://raw.githubusercontent.com/17mon/china_ip_list/master/china_ip_list.txt",
    "https://gitee.com/mirrors/china_ip_list/raw/master/china_ip_list.txt",
    "https://ispip.clang.cn/all_cn.txt",
    "https://ispip.clang.cn/all_cn_cidr.txt",
]

INTERNATIONAL_POOL_BACKUP_URLS: List[str] = []


class SsrfError(Exception):
    """SSRF 防护拦截异常。"""


MAX_SYNC_TIMEOUT = 120.0
MAX_REDIRECTS = 3


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise SsrfError(f"不支持的 URL 协议: {parsed.scheme}")
    if not parsed.netloc:
        raise SsrfError("URL 缺少主机名")
    hostname = parsed.hostname or ""
    if hostname.startswith(("127.", "10.", "192.168.", "172.")):
        raise SsrfError(f"禁止访问内网地址: {hostname}")
    if hostname in {"localhost", "0.0.0.0", "::1"}:
        raise SsrfError(f"禁止访问本地地址: {hostname}")


def _fetch_text(url: str, timeout: float) -> str:
    _validate_url(url)
    effective_timeout = min(float(timeout), MAX_SYNC_TIMEOUT)
    with httpx.Client(
        timeout=effective_timeout,
        follow_redirects=True,
        max_redirects=MAX_REDIRECTS,
    ) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text


def _fetch_with_fallback(urls: List[str], timeout: float = 60.0) -> tuple:
    """依次尝试多个 URL，返回 (text, used_url)。全部失败则抛出最后一个异常。"""
    last_exc = None
    for url in urls:
        try:
            text = _fetch_text(url, timeout=timeout)
            if text.strip():
                return text, url
        except Exception as exc:
            logger.warning("CIDR 数据源拉取失败: %s - %s", url, exc)
            last_exc = exc
            continue
    if last_exc:
        raise last_exc
    raise RuntimeError("无可用数据源")


def _get_china_pool_urls(cfg: IpGuardSettings) -> List[str]:
    urls = []
    primary = cfg.geo_china_pool_url.strip()
    if primary:
        urls.append(primary)
    for backup in CHINA_POOL_BACKUP_URLS:
        if backup not in urls:
            urls.append(backup)
    if cfg.geo_china_pool_backup_urls:
        for backup in cfg.geo_china_pool_backup_urls:
            if backup not in urls:
                urls.append(backup)
    return urls


def _get_international_pool_urls(cfg: IpGuardSettings) -> List[str]:
    urls = []
    primary = cfg.geo_international_pool_url.strip()
    if primary:
        urls.append(primary)
    for backup in INTERNATIONAL_POOL_BACKUP_URLS:
        if backup not in urls:
            urls.append(backup)
    if cfg.geo_international_pool_backup_urls:
        for backup in cfg.geo_international_pool_backup_urls:
            if backup not in urls:
                urls.append(backup)
    return urls


def sync_geo_pool(
    pool_key: str,
    url: str,
    cfg: IpGuardSettings,
    *,
    timeout: float = 60.0,
) -> Dict[str, Any]:
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
    except Exception as exc:
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


def sync_geo_pool_with_fallback(
    pool_key: str,
    urls: List[str],
    cfg: IpGuardSettings,
    *,
    timeout: float = 60.0,
) -> Dict[str, Any]:
    """多数据源备份同步：依次尝试，任一成功即返回。"""
    if not urls:
        msg = "无可用数据源 URL"
        IpGeoPoolStatus.objects.update_or_create(
            pool_key=pool_key,
            defaults={"source_url": "", "last_error": msg},
        )
        return {"ok": False, "pool_key": pool_key, "line_count": 0, "error": msg}

    cache = RedisCacheService(cfg.redis_url)
    last_error = ""

    for url in urls:
        try:
            text = _fetch_text(url, timeout=timeout)
            if not text.strip():
                continue

            index = build_index_from_text(text)
            if not index.get("v4_intervals") and not index.get("v6_nets"):
                logger.warning("数据源返回空索引: %s", url)
                continue

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
            logger.info(
                "地理 IP 池同步成功(多源): %s URL=%s 行数=%s v4区间=%s v6=%s",
                pool_key, url, index.get("line_count"), v4c, v6c,
            )
            return {
                "ok": True,
                "pool_key": pool_key,
                "source_url": url,
                "line_count": int(index.get("line_count") or 0),
                "v4_interval_count": v4c,
                "v6_net_count": v6c,
            }
        except Exception as exc:
            err = str(exc)
            logger.warning("CIDR 数据源失败: %s - %s", url, err)
            last_error = err
            continue

    IpGeoPoolStatus.objects.update_or_create(
        pool_key=pool_key,
        defaults={"source_url": urls[0][:512] if urls else "", "last_error": f"所有数据源均失败: {last_error[:500]}"},
    )
    return {"ok": False, "pool_key": pool_key, "line_count": 0, "error": f"所有数据源均失败: {last_error[:500]}"}


def sync_all_geo_pools(cfg: IpGuardSettings) -> Dict[str, Any]:
    results = []

    if cfg.geo_pool_multi_source_enabled:
        china_urls = _get_china_pool_urls(cfg)
        results.append(sync_geo_pool_with_fallback(POOL_CHINA, china_urls, cfg))
    else:
        results.append(sync_geo_pool(POOL_CHINA, cfg.geo_china_pool_url, cfg))

    intl_urls = _get_international_pool_urls(cfg)
    if intl_urls:
        if cfg.geo_pool_multi_source_enabled and len(intl_urls) > 1:
            results.append(sync_geo_pool_with_fallback(POOL_INTERNATIONAL, intl_urls, cfg))
        else:
            results.append(sync_geo_pool(POOL_INTERNATIONAL, cfg.geo_international_pool_url, cfg))
    else:
        results.append({
            "ok": False,
            "pool_key": POOL_INTERNATIONAL,
            "skipped": True,
            "message": "未配置国际池数据源，已跳过",
        })

    return {"results": results}
