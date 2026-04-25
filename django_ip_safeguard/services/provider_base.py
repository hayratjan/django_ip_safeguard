from abc import ABC, abstractmethod

from django_ip_safeguard.types import IpIntel


class BaseIpIntelProvider(ABC):
    """IP 情报服务抽象类。"""

    @abstractmethod
    def fetch_ip_intel(self, ip: str) -> IpIntel:
        """查询 IP 情报。"""
