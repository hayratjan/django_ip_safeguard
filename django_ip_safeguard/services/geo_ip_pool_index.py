"""将 CIDR 文本构建为可快速匹配的 IPv4 区间索引与 IPv6 网段列表。"""

from __future__ import annotations

import bisect
import ipaddress
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


def _merge_v4_intervals(networks: List[ipaddress.IPv4Network]) -> List[List[int]]:
    if not networks:
        return []
    intervals: List[Tuple[int, int]] = []
    for n in networks:
        lo = int(n.network_address)
        hi = int(n.broadcast_address)
        intervals.append((lo, hi))
    intervals.sort(key=lambda x: x[0])
    merged: List[List[int]] = []
    for lo, hi in intervals:
        if not merged or lo > merged[-1][1] + 1:
            merged.append([lo, hi])
        else:
            merged[-1][1] = max(merged[-1][1], hi)
    return merged


def build_index_from_text(text: str) -> Dict[str, Any]:
    """
    解析每行一个 CIDR 或单 IP 的文本，生成写入 Redis 的索引结构。
    IPv4 合并为有序不相交区间；IPv6 保留网段列表（量级通常较小）。
    """

    nets4: List[ipaddress.IPv4Network] = []
    nets6: List[ipaddress.IPv6Network] = []
    line_count = 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue
        line_count += 1
        try:
            net = ipaddress.ip_network(line, strict=False)
        except ValueError:
            continue
        if net.version == 4:
            nets4.append(net)  # type: ignore[arg-type]
        else:
            nets6.append(net)  # type: ignore[arg-type]

    v4_intervals = _merge_v4_intervals(nets4)
    v4_starts = [iv[0] for iv in v4_intervals]
    v6_nets = sorted({str(n) for n in nets6})
    return {
        "version": 1,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "line_count": line_count,
        "v4_intervals": v4_intervals,
        "v4_starts": v4_starts,
        "v6_nets": v6_nets,
    }


def ip_matches_index(client_ip: str, payload: Optional[dict]) -> bool:
    """判断 IP 是否落在索引定义的任意网段内。"""

    if not payload:
        return False
    try:
        addr = ipaddress.ip_address(client_ip)
    except ValueError:
        return False
    if addr.version == 4:
        intervals = payload.get("v4_intervals") or []
        starts = payload.get("v4_starts")
        if not intervals:
            return False
        x = int(addr)
        if starts and len(starts) == len(intervals):
            idx = bisect.bisect_right(starts, x) - 1
        else:
            starts = [iv[0] for iv in intervals]
            idx = bisect.bisect_right(starts, x) - 1
        if idx < 0:
            return False
        lo, hi = intervals[idx][0], intervals[idx][1]
        return lo <= x <= hi
    for s in payload.get("v6_nets") or []:
        try:
            if addr in ipaddress.ip_network(s, strict=False):
                return True
        except ValueError:
            continue
    return False


def index_has_cidr_data(payload: Optional[dict]) -> bool:
    if not payload:
        return False
    return bool(payload.get("v4_intervals") or payload.get("v6_nets"))
