from django_ip_safeguard.conf import IpGuardSettings
from django_ip_safeguard.types import IpIntel, RiskDecision


def evaluate_ip_risk(ip_intel: IpIntel, config: IpGuardSettings) -> RiskDecision:
    """按配置规则判定 IP 是否允许访问。"""

    local_risk_reasons = []

    if ip_intel.is_tor and "TOR" not in config.blocked_risk_tags and "tor" not in config.blocked_risk_tags:
        local_risk_reasons.append("Tor出口节点")

    if ip_intel.is_datacenter and config.blocked_risk_tags:
        dc_tags = {"datacenter", "DATACENTER"}
        if dc_tags & {t.upper() for t in config.blocked_risk_tags}:
            local_risk_reasons.append(f"数据中心ASN: {ip_intel.asn}({ip_intel.asn_org or ''})")

    if ip_intel.is_botnet:
        local_risk_reasons.append("僵尸网络IP")

    if ip_intel.risk_score >= config.risk_score_threshold:
        return RiskDecision(
            allow=False,
            reason=f"risk_score={ip_intel.risk_score} 超过阈值 {config.risk_score_threshold}",
            should_ban=True,
            ban_ttl=config.ban_ttl,
            local_risk_reasons=local_risk_reasons,
        )

    risk_tags = {t.lower() for t in ip_intel.risk_tags}
    blocked_tags = {t.lower() for t in config.blocked_risk_tags}
    if risk_tags & blocked_tags:
        return RiskDecision(
            allow=False,
            reason=f"命中风险标签: {sorted(risk_tags & blocked_tags)}",
            should_ban=True,
            ban_ttl=config.ban_ttl,
            local_risk_reasons=local_risk_reasons,
        )

    country_code = (ip_intel.country_code or "").upper()
    if config.allowed_countries and country_code not in config.allowed_countries:
        return RiskDecision(
            allow=False,
            reason=f"地区不在白名单: {country_code}",
            should_ban=False,
            local_risk_reasons=local_risk_reasons,
        )

    if config.blocked_countries and country_code in config.blocked_countries:
        return RiskDecision(
            allow=False,
            reason=f"地区命中黑名单: {country_code}",
            should_ban=False,
            local_risk_reasons=local_risk_reasons,
        )

    return RiskDecision(allow=True, reason="允许访问", local_risk_reasons=local_risk_reasons)
