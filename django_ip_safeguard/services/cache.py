import json
import time
from typing import Optional

import redis

from django_ip_safeguard.types import IpIntel

# 策略变更广播通道：所有 worker 收到后立刻清自己的进程内策略缓存
POLICY_INVALIDATE_CHANNEL = "ip_guard:policy:invalidate"


class RedisCacheService:
    """Redis 缓存服务，封装 IP 情报与封禁状态读写。"""

    def __init__(self, redis_url: str):
        self.client = redis.Redis.from_url(redis_url, decode_responses=True)

    def publish_policy_invalidate(self) -> None:
        """广播策略失效消息（多 worker 实时感知）。"""
        try:
            self.client.publish(POLICY_INVALIDATE_CHANNEL, "1")
        except Exception:  # noqa: BLE001
            return None

    def pubsub(self):
        """返回原生 pubsub 对象，由调用方负责订阅与生命周期。"""
        return self.client.pubsub()

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

    @staticmethod
    def _geo_pool_data_key(pool_key: str) -> str:
        return f"ip_guard:geo_pool:data:{pool_key}"

    def get_geo_pool_data(self, pool_key: str) -> Optional[str]:
        """读取地理 IP 池索引 JSON 字符串（无则 None）。"""

        try:
            return self.client.get(self._geo_pool_data_key(pool_key))
        except Exception:  # noqa: BLE001
            return None

    def set_geo_pool_data(self, pool_key: str, data: dict) -> None:
        """写入地理 IP 池索引（长期有效，由下次同步覆盖）。"""

        try:
            self.client.set(
                self._geo_pool_data_key(pool_key),
                json.dumps(data, separators=(",", ":")),
            )
        except Exception:  # noqa: BLE001
            return None

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
                        "country_name": ip_intel.country_name,
                        "region": ip_intel.region,
                        "city": ip_intel.city,
                        "latitude": ip_intel.latitude,
                        "longitude": ip_intel.longitude,
                        "asn": ip_intel.asn,
                        "asn_org": ip_intel.asn_org,
                        "is_datacenter": ip_intel.is_datacenter,
                        "is_proxy": ip_intel.is_proxy,
                        "is_vpn": ip_intel.is_vpn,
                        "is_tor": ip_intel.is_tor,
                        "is_botnet": ip_intel.is_botnet,
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

    def is_rate_limited(self, ip: str, max_per_minute: int, window_seconds: int = 60) -> bool:
        """滑动窗口限流：使用 Redis Sorted Set 记录请求时间戳，清理过期条目后统计窗口内数量。"""

        if max_per_minute <= 0:
            return False
        key = self._rate_limit_key(ip)
        now = time.time()
        window_start = now - window_seconds
        try:
            pipe = self.client.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {str(now): now})
            pipe.zcard(key)
            pipe.expire(key, window_seconds)
            _, _, count, _ = pipe.execute()
            return int(count) > max_per_minute
        except Exception:  # noqa: BLE001
            return False
