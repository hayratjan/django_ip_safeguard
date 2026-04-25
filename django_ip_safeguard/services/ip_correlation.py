import ipaddress
import json
import logging
import time
from typing import Dict, List, Optional

from django_ip_safeguard.conf import IpGuardSettings
from django_ip_safeguard.services.cache import RedisCacheService
from django_ip_safeguard.types import SubnetCorrelation

logger = logging.getLogger(__name__)


class IpCorrelationService:
    """
    IP 关联分析服务：
    - 同 C 段攻击关联检测
    - 子网热度统计
    - 攻击趋势分析
    """

    def __init__(self, cache_service: RedisCacheService, config: IpGuardSettings):
        self.cache = cache_service
        self.config = config

    def record_access(self, ip: str, is_blocked: bool) -> None:
        try:
            addr = ipaddress.ip_address(ip)
            if addr.version != 4:
                return
        except ValueError:
            return

        octets = str(ip).split(".")
        if len(octets) != 4:
            return

        subnet_c = ".".join(octets[:3])
        subnet_b = ".".join(octets[:2])

        now = time.time()
        window = 3600

        try:
            for prefix, level in [(subnet_c, "c"), (subnet_b, "b")]:
                key_total = f"ip_guard:correlation:{level}:{prefix}:total"
                key_blocked = f"ip_guard:correlation:{level}:{prefix}:blocked"
                key_ips = f"ip_guard:correlation:{level}:{prefix}:ips"

                pipe = self.cache.client.pipeline()
                pipe.zremrangebyscore(key_total, 0, now - window)
                pipe.zadd(key_total, {ip: now})
                pipe.expire(key_total, window)

                if is_blocked:
                    pipe.zremrangebyscore(key_blocked, 0, now - window)
                    pipe.zadd(key_blocked, {ip: now})
                    pipe.expire(key_blocked, window)

                pipe.sadd(key_ips, ip)
                pipe.expire(key_ips, window)
                pipe.execute()
        except Exception as exc:
            logger.debug("关联分析记录失败: %s", exc)

    def analyze_subnet(self, ip: str, level: str = "c") -> Optional[SubnetCorrelation]:
        try:
            addr = ipaddress.ip_address(ip)
            if addr.version != 4:
                return None
        except ValueError:
            return None

        octets = str(ip).split(".")
        if len(octets) != 4:
            return None

        if level == "c":
            subnet_prefix = ".".join(octets[:3])
            cidr = f"{subnet_prefix}.0/24"
        elif level == "b":
            subnet_prefix = ".".join(octets[:2])
            cidr = f"{subnet_prefix}.0.0/16"
        else:
            return None

        now = time.time()
        window = 3600

        try:
            key_total = f"ip_guard:correlation:{level}:{subnet_prefix}:total"
            key_blocked = f"ip_guard:correlation:{level}:{subnet_prefix}:blocked"
            key_ips = f"ip_guard:correlation:{level}:{subnet_prefix}:ips"

            pipe = self.cache.client.pipeline()
            pipe.zremrangebyscore(key_total, 0, now - window)
            pipe.zcard(key_total)
            pipe.zremrangebyscore(key_blocked, 0, now - window)
            pipe.zcard(key_blocked)
            pipe.smembers(key_ips)
            _, total, _, blocked, ip_set = pipe.execute()

            total = int(total) if total else 0
            blocked = int(blocked) if blocked else 0
            attack_ratio = round(blocked / total, 4) if total > 0 else 0.0

            correlated = list(ip_set or set())[:50]

            return SubnetCorrelation(
                subnet=cidr,
                total_ips=total,
                blocked_ips=blocked,
                attack_ratio=attack_ratio,
                correlated_ips=correlated,
            )
        except Exception as exc:
            logger.debug("子网关联分析失败: %s", exc)
            return None

    def get_hot_subnets(self, level: str = "c", top_n: int = 20) -> List[SubnetCorrelation]:
        pattern = f"ip_guard:correlation:{level}:*:total"
        try:
            keys = list(self.cache.client.scan_iter(match=pattern, count=100))[:200]
        except Exception:
            return []

        results = []
        now = time.time()
        window = 3600

        for key in keys:
            try:
                key_str = str(key)
                parts = key_str.split(":")
                if len(parts) < 4:
                    continue
                prefix = parts[3]

                subnet_prefix_key = f"ip_guard:correlation:{level}:{prefix}"
                key_total = f"{subnet_prefix_key}:total"
                key_blocked = f"{subnet_prefix_key}:blocked"

                pipe = self.cache.client.pipeline()
                pipe.zremrangebyscore(key_total, 0, now - window)
                pipe.zcard(key_total)
                pipe.zremrangebyscore(key_blocked, 0, now - window)
                pipe.zcard(key_blocked)
                _, total, _, blocked = pipe.execute()

                total = int(total) if total else 0
                blocked = int(blocked) if blocked else 0

                if total < 3:
                    continue

                attack_ratio = round(blocked / total, 4) if total > 0 else 0.0
                if level == "c":
                    cidr = f"{prefix}.0/24"
                else:
                    cidr = f"{prefix}.0.0/16"

                results.append(SubnetCorrelation(
                    subnet=cidr,
                    total_ips=total,
                    blocked_ips=blocked,
                    attack_ratio=attack_ratio,
                ))
            except Exception:
                continue

        results.sort(key=lambda x: x.attack_ratio, reverse=True)
        return results[:top_n]

    def check_subnet_attack(self, ip: str, threshold_ratio: float = 0.5, min_ips: int = 5) -> Optional[str]:
        correlation = self.analyze_subnet(ip, level="c")
        if not correlation:
            return None
        if correlation.total_ips >= min_ips and correlation.attack_ratio >= threshold_ratio:
            return f"同C段攻击关联({correlation.subnet}, 拦截率={correlation.attack_ratio:.0%}, {correlation.blocked_ips}/{correlation.total_ips}个IP)"
        return None
