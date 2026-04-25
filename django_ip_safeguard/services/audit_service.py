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
) -> None:
    """按开关记录访问决策到数据库。"""

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
