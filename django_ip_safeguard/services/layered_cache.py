import logging
import time
from typing import Dict, Optional, Tuple

from django_ip_safeguard.types import IpIntel

logger = logging.getLogger(__name__)

_L1_CACHE: Dict[str, Tuple[float, IpIntel]] = {}


class LayeredCacheService:
    """
    分层缓存服务：
    L1 - 进程内缓存（极短 TTL，热点 IP 加速）
    L2 - Redis 缓存（由 RedisCacheService 管理）
    L3 - 本地 GeoIP 数据库（由 GeoIP2LocalProvider 管理）
    L4 - HTTP API（由 Provider 管理）
    """

    def __init__(self, redis_cache, l1_ttl: float = 10.0, l1_max_size: int = 10000):
        self.redis_cache = redis_cache
        self.l1_ttl = l1_ttl
        self.l1_max_size = l1_max_size

    def get_ip_intel(self, ip: str) -> Optional[IpIntel]:
        result = self._l1_get(ip)
        if result is not None:
            return result

        result = self.redis_cache.get_ip_intel(ip)
        if result is not None:
            self._l1_set(ip, result)
            return result

        return None

    def set_ip_intel(self, ip_intel: IpIntel, ttl: int) -> None:
        self.redis_cache.set_ip_intel(ip_intel, ttl=ttl)
        self._l1_set(ip_intel.ip, ip_intel)

    def _l1_get(self, ip: str) -> Optional[IpIntel]:
        entry = _L1_CACHE.get(ip)
        if entry is None:
            return None
        expires_at, intel = entry
        if time.time() > expires_at:
            del _L1_CACHE[ip]
            return None
        return intel

    def _l1_set(self, ip: str, intel: IpIntel) -> None:
        if len(_L1_CACHE) >= self.l1_max_size:
            self._l1_evict()
        _L1_CACHE[ip] = (time.time() + self.l1_ttl, intel)

    def _l1_evict(self) -> None:
        now = time.time()
        expired_keys = [k for k, (exp, _) in _L1_CACHE.items() if now > exp]
        for k in expired_keys:
            del _L1_CACHE[k]
        if len(_L1_CACHE) >= self.l1_max_size:
            sorted_keys = sorted(_L1_CACHE.keys(), key=lambda k: _L1_CACHE[k][0])
            evict_count = len(_L1_CACHE) - self.l1_max_size // 2
            for k in sorted_keys[:evict_count]:
                del _L1_CACHE[k]

    @staticmethod
    def invalidate_l1_cache() -> None:
        _L1_CACHE.clear()

    def is_banned(self, ip: str) -> bool:
        return self.redis_cache.is_banned(ip)

    def set_ban(self, ip: str, reason: str, ttl: int) -> None:
        self.redis_cache.set_ban(ip=ip, reason=reason, ttl=ttl)

    def unban(self, ip: str) -> None:
        self.redis_cache.unban(ip)

    def is_rate_limited(self, ip: str, max_per_minute: int, window_seconds: int = 60) -> bool:
        return self.redis_cache.is_rate_limited(ip, max_per_minute, window_seconds)

    def acquire_intel_lock(self, ip: str, ttl: int) -> bool:
        return self.redis_cache.acquire_intel_lock(ip, ttl)

    def release_intel_lock(self, ip: str) -> None:
        self.redis_cache.release_intel_lock(ip)

    def ping(self) -> bool:
        return self.redis_cache.ping()
