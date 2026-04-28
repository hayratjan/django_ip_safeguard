"""策略路由：根据请求 host/path/method 在多条策略中选择第一条命中。

设计要点：
- 策略以 ``priority`` 升序遍历，第一条命中即返回；找不到时返回兜底策略（通常是 ``name="default"``）。
- 任意 match_* 字段为空表示不限制；正则 / 路径前缀 / 方法三者全部满足才视为命中。
- 这里不直接读 Django ORM，由 :func:`policy_service.load_effective_policy` 把策略行序列化成 ``CompiledPolicy`` 后传入。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class CompiledPolicy:
    """策略行的内存结构（与 Django model 字段一一对应）。"""

    name: str
    priority: int
    enabled: bool
    match_host_regex: str = ""
    match_path_prefixes: Tuple[str, ...] = field(default_factory=tuple)
    match_methods: Tuple[str, ...] = field(default_factory=tuple)
    raw: dict = field(default_factory=dict)

    def host_pattern(self) -> Optional[re.Pattern]:
        if not self.match_host_regex:
            return None
        try:
            return re.compile(self.match_host_regex)
        except re.error:
            return None

    def matches(self, host: str, path: str, method: str) -> bool:
        host_pat = self.host_pattern()
        if host_pat is not None and not host_pat.search(host or ""):
            return False
        if self.match_path_prefixes:
            if not any(path.startswith(p) for p in self.match_path_prefixes if p):
                return False
        if self.match_methods:
            allowed = {m.strip().upper() for m in self.match_methods if m}
            if method.upper() not in allowed:
                return False
        return True


def select_policy(
    policies: Sequence[CompiledPolicy],
    host: str,
    path: str,
    method: str,
) -> Optional[CompiledPolicy]:
    """按 priority 升序，返回第一条命中的策略；未命中返回 None。

    禁用（``enabled=False``）的策略会被跳过，由上层根据 fallback 决定行为。
    """

    sorted_policies: List[CompiledPolicy] = sorted(policies, key=lambda p: (p.priority, p.name))
    for policy in sorted_policies:
        if not policy.enabled:
            continue
        if policy.matches(host, path, method):
            return policy
    return None
