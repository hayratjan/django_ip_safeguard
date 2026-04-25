"""IP 与单条规则（精确或 CIDR）匹配，供白名单/黑名单复用。"""

from __future__ import annotations

import ipaddress
from typing import Iterable, Tuple


def ip_matches_rule(client_ip: str, rule: str) -> bool:
    """判断 client_ip 是否命中一条规则：单 IP 或 CIDR 网段。"""

    rule = (rule or "").strip()
    if not rule or not client_ip:
        return False
    try:
        addr = ipaddress.ip_address(client_ip.strip())
    except ValueError:
        return False
    if "/" in rule:
        try:
            net = ipaddress.ip_network(rule, strict=False)
        except ValueError:
            return False
        return addr in net
    try:
        other = ipaddress.ip_address(rule)
    except ValueError:
        return False
    return addr == other


def first_matching_rule(client_ip: str, rules: Iterable[str]) -> Tuple[bool, str]:
    """若命中规则，返回 (True, 命中的规则原文)；否则 (False, '')。"""

    for raw in rules:
        r = str(raw).strip()
        if not r:
            continue
        if ip_matches_rule(client_ip, r):
            return True, r
    return False, ""
