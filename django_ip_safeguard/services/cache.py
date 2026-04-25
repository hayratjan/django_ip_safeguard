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

    def get_ip_intel(self, ip: str) -> Optional[IpIntel]:
        raw = self.client.get(self._intel_key(ip))
        if not raw:
            return None
        data = json.loads(raw)
        return IpIntel(**data)

    def set_ip_intel(self, ip_intel: IpIntel, ttl: int) -> None:
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

    def is_banned(self, ip: str) -> bool:
        return bool(self.client.get(self._ban_key(ip)))

    def set_ban(self, ip: str, reason: str, ttl: int) -> None:
        self.client.setex(self._ban_key(ip), ttl, reason)
