"""加权评估单测：覆盖分级阈值与动作映射。"""

from django_ip_safeguard.conf import IpGuardSettings
from django_ip_safeguard.services.risk_engine import evaluate_ip_risk_v2
from django_ip_safeguard.types import IpIntel


def _cfg(**kw):
    return IpGuardSettings(
        risk_score_threshold=200,  # 故意设高，避免老路径短路
        tier_medium=kw.pop("medium", 40),
        tier_high=kw.pop("high", 80),
        medium_action=kw.pop("medium_action", "block"),
        high_action=kw.pop("high_action", "ban"),
        signal_weights=kw.pop("signal_weights", {}),
        blocked_risk_tags=kw.pop("blocked_risk_tags", ("vpn",)),
        **kw,
    )


def test_clean_intel_is_allowed():
    decision = evaluate_ip_risk_v2(IpIntel(ip="1.1.1.1", risk_score=10), _cfg())
    assert decision.allow is True
    assert decision.action == "allow"
    # weight 默认 risk_score=1.0，10 分不够 medium=40
    assert decision.score == 10.0


def test_medium_tier_returns_medium_action():
    decision = evaluate_ip_risk_v2(IpIntel(ip="1.1.1.1", risk_score=50), _cfg())
    assert decision.allow is False
    assert decision.action == "block"
    assert decision.should_ban is False


def test_high_tier_triggers_ban_with_ttl():
    cfg = _cfg(medium=40, high=80, ban_ttl=60)
    decision = evaluate_ip_risk_v2(IpIntel(ip="1.1.1.1", risk_score=120), cfg)
    assert decision.allow is False
    assert decision.action == "ban"
    assert decision.should_ban is True
    assert decision.ban_ttl == 60


def test_tag_weight_pushes_into_high():
    cfg = _cfg(signal_weights={"risk_score": 0, "tag_blocked": 100}, blocked_risk_tags=("vpn",))
    decision = evaluate_ip_risk_v2(
        IpIntel(ip="1.1.1.1", risk_score=0, risk_tags=["vpn"]), cfg,
    )
    assert decision.action == "ban"
    assert any("vpn" in r.lower() for r in decision.score_reasons)


def test_country_blocked_signal():
    cfg = _cfg(
        blocked_countries=("RU",),
        signal_weights={"risk_score": 0, "country_blocked": 100},
    )
    d = evaluate_ip_risk_v2(IpIntel(ip="1.1.1.1", country_code="RU", risk_score=0), cfg)
    assert d.action == "ban"


def test_challenge_action_is_supported():
    cfg = _cfg(medium_action="challenge", challenge_status_code=429, medium=40)
    d = evaluate_ip_risk_v2(IpIntel(ip="1.1.1.1", risk_score=50), cfg)
    assert d.action == "challenge"
    assert d.allow is False
    assert d.challenge_status_code == 429
