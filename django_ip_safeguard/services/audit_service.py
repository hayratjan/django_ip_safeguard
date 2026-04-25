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
    if not enabled:
        return
    try:
        from django_ip_safeguard.models import IpAccessLog

        IpAccessLog.objects.create(
            ip=ip,
            country_code=(ip_intel.country_code or "")[:16],
            country_name=(ip_intel.country_name or "")[:64],
            region=(ip_intel.region or "")[:64],
            city=(ip_intel.city or "")[:64],
            asn=ip_intel.asn,
            asn_org=(ip_intel.asn_org or "")[:128],
            is_datacenter=ip_intel.is_datacenter,
            is_proxy=ip_intel.is_proxy,
            is_vpn=ip_intel.is_vpn,
            is_tor=ip_intel.is_tor,
            risk_score=ip_intel.risk_score,
            risk_tags=ip_intel.risk_tags,
            decision=decision,
            reason=reason[:255],
            path=path[:255],
        )
    except Exception as exc:
        logger.warning("写入 IP 审计日志失败: %s", exc)


def mask_ip(ip: str, enabled: bool, keep_prefix: int) -> str:
    if not enabled:
        return ip
    if ":" in ip:
        parts = ip.split(":")
        keep = max(1, min(len(parts), keep_prefix))
        return ":".join(parts[:keep] + ["****"])
    parts = ip.split(".")
    if len(parts) != 4:
        return ip
    keep = max(1, min(3, keep_prefix))
    masked = parts[:keep] + ["*"] * (4 - keep)
    return ".".join(masked)
