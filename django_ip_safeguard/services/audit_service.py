import logging

from django_ip_safeguard.types import IpIntel

logger = logging.getLogger(__name__)


def log_access_decision(
    *,
    enabled: bool,
    ip: str,
    path: str,
    decision: str,
    reason: str,
    ip_intel: IpIntel,
    ip_mask_enabled: bool = True,
    ip_mask_keep_prefix: int = 2,
) -> None:
    """按开关记录访问决策到数据库。始终存储完整 IP，脱敏在展示层按配置执行。"""

    if not enabled:
        return
    try:
        from django_ip_safeguard.models import IpAccessLog

        IpAccessLog.objects.create(
            ip=ip,
            country_code=(ip_intel.country_code or "")[:16],
            risk_score=ip_intel.risk_score,
            risk_tags=ip_intel.risk_tags,
            decision=decision,
            reason=reason[:255],
            path=path[:255],
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("写入 IP 审计日志失败: %s", exc)


def mask_ip(ip: str, enabled: bool, keep_prefix: int) -> str:
    """按配置掩码处理 IP，降低敏感数据暴露风险。"""

    if not enabled:
        return ip
    if ":" in ip:
        # IPv6 仅保留前 keep_prefix 段
        parts = ip.split(":")
        keep = max(1, min(len(parts), keep_prefix))
        return ":".join(parts[:keep] + ["****"])
    parts = ip.split(".")
    if len(parts) != 4:
        return ip
    keep = max(1, min(3, keep_prefix))
    masked = parts[:keep] + ["*"] * (4 - keep)
    return ".".join(masked)
