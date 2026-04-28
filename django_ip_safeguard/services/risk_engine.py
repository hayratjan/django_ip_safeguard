"""加权风险打分与分级动作判定。

设计：
- 把每个信号映射成 ``(weight_key, points, reason)``，分数 = sum(points * weight)。
- 阈值分级：score < medium → ``allow``；medium ≤ score < high → ``medium_action``；score ≥ high → ``high_action``。
- 兼容旧接口 :func:`evaluate_ip_risk`：仍返回 ``RiskDecision(allow, reason, should_ban, ban_ttl)``，
  同时填充新字段 ``action / score / score_reasons``，使中间件可两套逻辑共存。
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from django_ip_safeguard.conf import IpGuardSettings
from django_ip_safeguard.services.policy_service import DEFAULT_SIGNAL_WEIGHTS
from django_ip_safeguard.types import IpIntel, RiskDecision

# 不再做风险判定、直接放行的动作
PASS_ACTIONS = frozenset({"allow", "log_only"})
# 视为拦截类的动作（中间件据此构造响应 + 写审计）
BLOCK_ACTIONS = frozenset({"block", "ban", "challenge", "rate_limit"})


def _weight(config: IpGuardSettings, key: str) -> float:
    weights = dict(DEFAULT_SIGNAL_WEIGHTS)
    if config.signal_weights:
        weights.update({k: float(v) for k, v in config.signal_weights.items()})
    return float(weights.get(key, 0.0))


def _is_unknown_country(country_code: Optional[str]) -> bool:
    c = (country_code or "").strip().upper()
    return not c or c == "UNKNOWN"


def _collect_signals(ip_intel: IpIntel, config: IpGuardSettings) -> Tuple[List[Tuple[str, str, float]], List[str]]:
    """返回 [(信号键, 原因, 分值)] 与 local_risk_reasons。"""
    signals: List[Tuple[str, str, float]] = []
    local_reasons: List[str] = []
    mode = (getattr(config, "country_mode", None) or "default").lower()

    # 风险分本身按权重折算（weight=1.0 即原值），不强行过阈值
    rs = int(ip_intel.risk_score or 0)
    if rs > 0:
        signals.append(("risk_score", f"risk_score={rs}", _weight(config, "risk_score") * rs))

    blocked_tags_lower = {t.lower() for t in config.blocked_risk_tags}
    intel_tags_lower = {t.lower() for t in (ip_intel.risk_tags or [])}
    hit_tags = sorted(intel_tags_lower & blocked_tags_lower)
    if hit_tags:
        signals.append(("tag_blocked", f"命中风险标签: {hit_tags}", _weight(config, "tag_blocked")))

    country = (ip_intel.country_code or "").upper()
    # allowlist / blacklist 模式由国家门控单独处理，避免与加权重复计分
    if mode == "default":
        if config.allowed_countries and country and country not in config.allowed_countries:
            signals.append(("country_not_allowed", f"地区不在白名单: {country}", _weight(config, "country_not_allowed")))
        if config.blocked_countries and country and country in config.blocked_countries:
            signals.append(("country_blocked", f"地区命中黑名单: {country}", _weight(config, "country_blocked")))
    elif mode == "allowlist":
        if config.blocked_countries and country and country in config.blocked_countries:
            signals.append(("country_blocked", f"地区命中黑名单: {country}", _weight(config, "country_blocked")))
    else:  # blacklist
        if config.blocked_countries and country and country in config.blocked_countries:
            signals.append(("country_blocked", f"地区命中黑名单: {country}", _weight(config, "country_blocked")))

    if ip_intel.is_tor:
        local_reasons.append("Tor出口节点")
        signals.append(("tor", "Tor出口节点", _weight(config, "tor")))
    if ip_intel.is_botnet:
        local_reasons.append("僵尸网络IP")
        signals.append(("botnet", "僵尸网络IP", _weight(config, "botnet")))
    if ip_intel.is_datacenter:
        local_reasons.append(f"数据中心ASN: {ip_intel.asn}({ip_intel.asn_org or ''})")
        if "datacenter" in {t.lower() for t in config.blocked_risk_tags}:
            signals.append(("datacenter", local_reasons[-1], _weight(config, "datacenter")))

    return signals, local_reasons


def _decide_action(score: float, config: IpGuardSettings) -> str:
    """根据 tier_medium / tier_high 选择动作字符串。"""
    if score >= config.tier_high:
        return config.high_action or "ban"
    if score >= config.tier_medium:
        return config.medium_action or "block"
    return "allow"


def evaluate_country_mode_gate(ip_intel: IpIntel, config: IpGuardSettings) -> Optional[RiskDecision]:
    """按 country_mode 做明确国家策略；返回 None 表示本层不拦截。"""
    mode = (getattr(config, "country_mode", None) or "default").lower()
    if mode == "default":
        return None

    cc = (ip_intel.country_code or "").strip().upper()
    blocked = tuple(config.blocked_countries or ())
    allowed = tuple(config.allowed_countries or ())

    if mode == "allowlist":
        if not allowed:
            return None
        if _is_unknown_country(ip_intel.country_code):
            if getattr(config, "block_unknown_country", True):
                return RiskDecision(
                    allow=False,
                    reason="国家/地区未知或未识别，未命中允许列表",
                    should_ban=False,
                    local_risk_reasons=[],
                    action="block",
                    score=0.0,
                    score_reasons=["国家未知"],
                )
            return None
        if cc not in allowed:
            return RiskDecision(
                allow=False,
                reason=f"国家不在允许列表: {cc}",
                should_ban=False,
                local_risk_reasons=[],
                action="block",
                score=0.0,
                score_reasons=[f"不在允许列表: {cc}"],
            )
        if blocked and cc in blocked:
            return RiskDecision(
                allow=False,
                reason=f"国家命中禁止列表: {cc}",
                should_ban=False,
                local_risk_reasons=[],
                action="block",
                score=0.0,
                score_reasons=[f"命中禁止列表: {cc}"],
            )
        return None

    if mode == "blacklist":
        if blocked and cc and cc in blocked:
            return RiskDecision(
                allow=False,
                reason=f"国家命中黑名单: {cc}",
                should_ban=False,
                local_risk_reasons=[],
                action="block",
                score=0.0,
                score_reasons=[f"命中黑名单: {cc}"],
            )
        return None

    return None


def evaluate_ip_risk_v2(ip_intel: IpIntel, config: IpGuardSettings) -> RiskDecision:
    """新版加权评估，返回带 action / score 的 RiskDecision。"""
    signals, local_reasons = _collect_signals(ip_intel, config)
    score = sum(p for _, _, p in signals)
    score_reasons = [r for _, r, _ in signals]

    action = _decide_action(score, config)
    reason = "; ".join(score_reasons) if score_reasons else "允许访问"

    if action in PASS_ACTIONS:
        return RiskDecision(
            allow=True,
            reason=reason,
            should_ban=False,
            local_risk_reasons=local_reasons,
            action=action,
            score=score,
            score_reasons=score_reasons,
        )

    return RiskDecision(
        allow=False,
        reason=reason,
        should_ban=(action == "ban"),
        ban_ttl=config.ban_ttl if action == "ban" else None,
        local_risk_reasons=local_reasons,
        action=action,
        score=score,
        score_reasons=score_reasons,
        challenge_status_code=config.challenge_status_code if action == "challenge" else None,
    )


def evaluate_ip_risk(ip_intel: IpIntel, config: IpGuardSettings) -> RiskDecision:
    """兼容旧接口：默认走加权评估，但保留旧的"首命中即拦截"语义作为短路。

    - 风险分超阈值：直接 ban（与旧版一致，便于历史调用方）。
    - 否则走加权评估；若加权未拦截，再做一次国家白/黑名单的"硬"判定（旧 API 行为兼容）。
    """
    if int(ip_intel.risk_score or 0) >= int(config.risk_score_threshold or 0):
        reason = f"risk_score={ip_intel.risk_score} 超过阈值 {config.risk_score_threshold}"
        signals, local_reasons = _collect_signals(ip_intel, config)
        return RiskDecision(
            allow=False,
            reason=reason,
            should_ban=True,
            ban_ttl=config.ban_ttl,
            local_risk_reasons=local_reasons,
            action="ban",
            score=sum(p for _, _, p in signals),
            score_reasons=[r for _, r, _ in signals] or [reason],
        )

    decision = evaluate_ip_risk_v2(ip_intel, config)
    if not decision.allow:
        return decision

    gated = evaluate_country_mode_gate(ip_intel, config)
    if gated is not None:
        return RiskDecision(
            allow=False,
            reason=gated.reason,
            should_ban=False,
            local_risk_reasons=decision.local_risk_reasons,
            action="block",
            score=decision.score,
            score_reasons=list(decision.score_reasons) + list(gated.score_reasons),
        )

    mode = (getattr(config, "country_mode", None) or "default").lower()
    if mode != "default":
        return decision

    country_code = (ip_intel.country_code or "").upper()
    if config.allowed_countries and country_code and country_code not in config.allowed_countries:
        return RiskDecision(
            allow=False,
            reason=f"地区不在白名单: {country_code}",
            should_ban=False,
            local_risk_reasons=decision.local_risk_reasons,
            action="block",
            score=decision.score,
            score_reasons=decision.score_reasons,
        )
    if config.blocked_countries and country_code and country_code in config.blocked_countries:
        return RiskDecision(
            allow=False,
            reason=f"地区命中黑名单: {country_code}",
            should_ban=False,
            local_risk_reasons=decision.local_risk_reasons,
            action="block",
            score=decision.score,
            score_reasons=decision.score_reasons,
        )
    return decision
