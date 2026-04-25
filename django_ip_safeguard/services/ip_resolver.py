import ipaddress
import logging
from typing import Iterable, Optional

from django.http import HttpRequest

logger = logging.getLogger(__name__)


def _is_valid_ip(ip: str) -> bool:
    """校验字符串是否为有效 IPv4 或 IPv6 地址。"""
    if not ip:
        return False
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def _in_trusted_proxy(remote_addr: str, trusted_proxy_cidrs: Iterable[str]) -> bool:
    if not remote_addr or not trusted_proxy_cidrs:
        return False
    try:
        remote_ip = ipaddress.ip_address(remote_addr)
    except ValueError:
        return False
    for cidr in trusted_proxy_cidrs:
        try:
            if remote_ip in ipaddress.ip_network(cidr, strict=False):
                return True
        except ValueError:
            continue
    return False


def resolve_client_ip(request: HttpRequest, trusted_proxy_cidrs: Iterable[str]) -> Optional[str]:
    """解析客户端真实 IP，仅在受信代理场景下解析 X-Forwarded-For。

    返回 None 表示无法解析出有效 IP。
    """
    remote_addr = (request.META.get("REMOTE_ADDR") or "").strip()
    xff = (request.META.get("HTTP_X_FORWARDED_FOR") or "").strip()

    if xff:
        if _in_trusted_proxy(remote_addr, trusted_proxy_cidrs):
            first = xff.split(",")[0].strip()
            if first and _is_valid_ip(first):
                return first
            logger.warning(
                "X-Forwarded-For 首个 IP 无效: first=%s, remote_addr=%s",
                first,
                remote_addr,
            )
        else:
            logger.warning(
                "收到 X-Forwarded-For 但 REMOTE_ADDR 不在信任代理列表: "
                "xff=%s, remote_addr=%s, trusted=%s",
                xff,
                remote_addr,
                trusted_proxy_cidrs,
            )

    if remote_addr and _is_valid_ip(remote_addr):
        return remote_addr

    return None
