from django_ip_safeguard.conf import IpGuardSettings
from django_ip_safeguard.types import IpIntel, RiskDecision


def evaluate_ip_risk(ip_intel: IpIntel, config: IpGuardSettings) -> RiskDecision:
    """按配置规则判定 IP 是否允许访问。"""

    if ip_intel.risk_score >= config.risk_score_threshold:
        return RiskDecision(
            allow=False,
            reason=f"risk_score={ip_intel.risk_score} 超过阈值 {config.risk_score_threshold}",
            should_ban=True,
            ban_ttl=config.ban_ttl,
        )

    risk_tags = {t.lower() for t in ip_intel.risk_tags}
    blocked_tags = {t.lower() for t in config.blocked_risk_tags}
    if risk_tags & blocked_tags:
        return RiskDecision(
            allow=False,
            reason=f"命中风险标签: {sorted(risk_tags & blocked_tags)}",
            should_ban=True,
            ban_ttl=config.ban_ttl,
        )

    country_code = (ip_intel.country_code or "").upper()
    if config.allowed_countries and country_code not in config.allowed_countries:
        return RiskDecision(allow=False, reason=f"地区不在白名单: {country_code}", should_ban=False)

    if config.blocked_countries and country_code in config.blocked_countries:
        return RiskDecision(allow=False, reason=f"地区命中黑名单: {country_code}", should_ban=False)

    return RiskDecision(allow=True, reason="允许访问")
