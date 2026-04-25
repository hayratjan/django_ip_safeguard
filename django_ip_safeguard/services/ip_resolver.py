import ipaddress
from typing import Iterable

from django.http import HttpRequest


def _in_trusted_proxy(remote_addr: str, trusted_proxy_cidrs: Iterable[str]) -> bool:
    if not remote_addr or not trusted_proxy_cidrs:
        return False
    remote_ip = ipaddress.ip_address(remote_addr)
    for cidr in trusted_proxy_cidrs:
        if remote_ip in ipaddress.ip_network(cidr, strict=False):
            return True
    return False


def resolve_client_ip(request: HttpRequest, trusted_proxy_cidrs: Iterable[str]) -> str:
    """解析客户端真实 IP，仅在受信代理场景下解析 X-Forwarded-For。"""

    remote_addr = (request.META.get("REMOTE_ADDR") or "").strip()
    xff = (request.META.get("HTTP_X_FORWARDED_FOR") or "").strip()

    if xff and _in_trusted_proxy(remote_addr, trusted_proxy_cidrs):
        # XFF 第一个通常为客户端原始 IP
        first = xff.split(",")[0].strip()
        if first:
            return first
    return remote_addr
