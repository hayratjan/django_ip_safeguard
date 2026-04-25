from django_ip_safeguard.conf import IpGuardSettings
from django_ip_safeguard.services.risk_engine import evaluate_ip_risk
from django_ip_safeguard.types import IpIntel


def test_should_block_when_risk_score_exceeds_threshold():
    cfg = IpGuardSettings(risk_score_threshold=50)
    intel = IpIntel(ip="1.1.1.1", risk_score=90)
    decision = evaluate_ip_risk(intel, cfg)
    assert decision.allow is False
    assert decision.should_ban is True


def test_should_block_when_country_not_in_allow_list():
    cfg = IpGuardSettings(allowed_countries=("CN", "SG"))
    intel = IpIntel(ip="8.8.8.8", country_code="US", risk_score=0)
    decision = evaluate_ip_risk(intel, cfg)
    assert decision.allow is False
    assert "白名单" in decision.reason


def test_should_allow_when_clean():
    cfg = IpGuardSettings(risk_score_threshold=80, blocked_countries=("RU",))
    intel = IpIntel(ip="114.114.114.114", country_code="CN", risk_score=10, risk_tags=[])
    decision = evaluate_ip_risk(intel, cfg)
    assert decision.allow is True
