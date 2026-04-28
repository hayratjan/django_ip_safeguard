"""结构化决策日志：单行 JSON，便于日志采集（ELK / Loki）。

默认关闭，设置 ``IP_GUARD_STRUCTURED_DECISION_LOGGING=True`` 启用。
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

_logger = logging.getLogger("django_ip_safeguard.decision")


def log_structured_decision(
    *,
    policy_name: str,
    branch: str,
    allowed: bool,
    action: Optional[str] = None,
    path: str = "",
    method: str = "",
    ip_masked: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """输出一条 INFO 级别 JSON 行；字段固定便于检索。"""
    payload: Dict[str, Any] = {
        "event": "ip_guard_decision",
        "policy": policy_name or "default",
        "branch": branch,
        "allowed": allowed,
        "path": path[:512],
        "method": (method or "").upper()[:16],
        "ip": ip_masked[:64],
    }
    if action:
        payload["action"] = action
    if extra:
        payload["extra"] = extra
    try:
        _logger.info("%s", json.dumps(payload, ensure_ascii=False))
    except Exception:  # noqa: BLE001
        _logger.info("ip_guard_decision fallback policy=%s branch=%s allowed=%s", policy_name, branch, allowed)
