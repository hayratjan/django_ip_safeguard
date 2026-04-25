import json
from typing import Optional

import redis

from django_ip_safeguard.types import IpIntel


class RedisCacheService:
    """Redis 缓存服务，封装 IP 情报与封禁状态读写。"""

    def __init__(self, redis_url: str):
        self.client = redis.Redis.from_url(redis_url, decode_responses=True)

    @staticmethod
    def _intel_key(ip: str) -> str:
        return f"ip_guard:intel:{ip}"

    @staticmethod
    def _ban_key(ip: str) -> str:
        return f"ip_guard:ban:{ip}"

    @staticmethod
    def _dedupe_key(ip: str) -> str:
        return f"ip_guard:lock:intel:{ip}"

    @staticmethod
    def _circuit_key() -> str:
        return "ip_guard:provider:circuit_failures"

    @staticmethod
    def _rate_limit_key(ip: str) -> str:
        return f"ip_guard:ratelimit:{ip}"

    def get_ip_intel(self, ip: str) -> Optional[IpIntel]:
        try:
            raw = self.client.get(self._intel_key(ip))
            if not raw:
                return None
            data = json.loads(raw)
            return IpIntel(**data)
        except Exception:  # noqa: BLE001
            return None

    def set_ip_intel(self, ip_intel: IpIntel, ttl: int) -> None:
        try:
            self.client.setex(
                self._intel_key(ip_intel.ip),
                ttl,
                json.dumps(
                    {
                        "ip": ip_intel.ip,
                        "country_code": ip_intel.country_code,
                        "risk_score": ip_intel.risk_score,
                        "risk_tags": ip_intel.risk_tags,
                        "source": ip_intel.source,
                    }
                ),
            )
        except Exception:  # noqa: BLE001
            return None

    def is_banned(self, ip: str) -> bool:
        try:
            return bool(self.client.get(self._ban_key(ip)))
        except Exception:  # noqa: BLE001
            return False

    def set_ban(self, ip: str, reason: str, ttl: int) -> None:
        try:
            self.client.setex(self._ban_key(ip), ttl, reason)
        except Exception:  # noqa: BLE001
            return None

    def unban(self, ip: str) -> None:
        try:
            self.client.delete(self._ban_key(ip))
        except Exception:  # noqa: BLE001
            return None

    def ping(self) -> bool:
        try:
            return bool(self.client.ping())
        except Exception:  # noqa: BLE001
            return False

    def acquire_intel_lock(self, ip: str, ttl: int) -> bool:
        try:
            return bool(self.client.set(self._dedupe_key(ip), "1", nx=True, ex=ttl))
        except Exception:  # noqa: BLE001
            return False

    def release_intel_lock(self, ip: str) -> None:
        try:
            self.client.delete(self._dedupe_key(ip))
        except Exception:  # noqa: BLE001
            return None

    def increase_provider_failures(self, ttl: int) -> int:
        try:
            count = self.client.incr(self._circuit_key())
            if count == 1:
                self.client.expire(self._circuit_key(), ttl)
            return int(count)
        except Exception:  # noqa: BLE001
            return 0

    def clear_provider_failures(self) -> None:
        try:
            self.client.delete(self._circuit_key())
        except Exception:  # noqa: BLE001
            return None

    def get_provider_failures(self) -> int:
        try:
            raw = self.client.get(self._circuit_key())
            if raw is None:
                return 0
            return int(raw)
        except Exception:  # noqa: BLE001
            return 0

    def is_rate_limited(self, ip: str, max_per_minute: int) -> bool:
        """滑动窗口：自首次请求起 60 秒内计数，超过 max 则视为限流（max<=0 不启用）。"""

        if max_per_minute <= 0:
            return False
        key = self._rate_limit_key(ip)
        try:
            count = int(self.client.incr(key))
            if count == 1:
                self.client.expire(key, 60)
            return count > max_per_minute
        except Exception:  # noqa: BLE001
            return False
