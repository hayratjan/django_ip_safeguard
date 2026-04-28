"""Redis 聚合决策计数：跨 worker 累计，供 /api/metrics/ 展示。

使用单个 HASH 键 ``ip_guard:metrics:counters``，字段名短前缀：
- ``total``：总请求计数（中间件实际评估路径）
- ``d_allow`` / ``d_block``：最终放行 / 拦截（与审计 decision 对齐）
- ``b_*``：分支：skip_path、disabled、whitelist、blacklist、geo_pool、ratelimit、banned、intel_fail_open、intel_fail_close、risk
- ``a_*``：动作（风险分支）：allow、log_only、block、ban、challenge、rate_limit
- ``p_<策略名>``：命中该策略路由的请求数（策略名仅保留 [A-Za-z0-9_-]，过长截断）
"""

from __future__ import annotations

import re
from typing import Optional

REDIS_METRICS_HASH_KEY = "ip_guard:metrics:counters"

_POLICY_FIELD_RE = re.compile(r"[^a-zA-Z0-9_-]+")


def _sanitize_policy_field(name: str) -> str:
    s = _POLICY_FIELD_RE.sub("_", (name or "default").strip())[:64].strip("_") or "default"
    return f"p_{s}"


def record_decision_counters(
    redis_url: str,
    *,
    policy_name: str = "",
    branch: str = "",
    allowed: bool = True,
    action: Optional[str] = None,
) -> None:
    """单次请求结束时增量计数；Redis 不可用时静默跳过。"""
    try:
        import redis

        client = redis.Redis.from_url(redis_url, decode_responses=True)
        pipe = client.pipeline()
        # 跳过路径不计入 total，避免与健康检查流量混淆
        if branch == "skip_path":
            pipe.hincrby(REDIS_METRICS_HASH_KEY, "skipped_paths", 1)
            pipe.hincrby(REDIS_METRICS_HASH_KEY, "b_skip_path", 1)
            pipe.execute()
            return

        pipe.hincrby(REDIS_METRICS_HASH_KEY, "total", 1)
        if policy_name:
            pipe.hincrby(REDIS_METRICS_HASH_KEY, _sanitize_policy_field(policy_name), 1)
        pipe.hincrby(REDIS_METRICS_HASH_KEY, "d_allow" if allowed else "d_block", 1)
        b_key = f"b_{branch}"
        if branch and len(b_key) <= 48:
            pipe.hincrby(REDIS_METRICS_HASH_KEY, b_key, 1)
        if action and branch == "risk":
            ak = f"a_{action}"
            if len(ak) <= 32:
                pipe.hincrby(REDIS_METRICS_HASH_KEY, ak, 1)
        pipe.execute()
    except Exception:  # noqa: BLE001
        return None


def fetch_decision_counters(redis_url: str) -> dict:
    """读取 HASH 全部字段为 {field: int}。"""
    try:
        import redis

        client = redis.Redis.from_url(redis_url, decode_responses=True)
        raw = client.hgetall(REDIS_METRICS_HASH_KEY)
        out = {}
        for k, v in (raw or {}).items():
            try:
                out[str(k)] = int(v)
            except (TypeError, ValueError):
                out[str(k)] = 0
        return out
    except Exception:  # noqa: BLE001
        return {}


def reset_decision_counters(redis_url: str) -> bool:
    """清空计数 HASH（管理接口用）。"""
    try:
        import redis

        client = redis.Redis.from_url(redis_url, decode_responses=True)
        client.delete(REDIS_METRICS_HASH_KEY)
        return True
    except Exception:  # noqa: BLE001
        return False
