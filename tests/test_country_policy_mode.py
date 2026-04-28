"""国家策略模式：allowlist / blacklist 与 evaluate_ip_risk 门控。"""

from django_ip_safeguard.conf import IpGuardSettings
from django_ip_safeguard.services.risk_engine import evaluate_ip_risk
from django_ip_safeguard.types import IpIntel


def _cfg(**kw) -> IpGuardSettings:
    base = dict(
        risk_score_threshold=200,
        tier_medium=40,
        tier_high=80,
        medium_action="block",
        high_action="ban",
        signal_weights={"risk_score": 0.0},
        blocked_risk_tags=(),
        allowed_countries=(),
        blocked_countries=(),
        country_mode="default",
        block_unknown_country=True,
        ban_ttl=3600,
        challenge_status_code=403,
    )
    base.update(kw)
    return IpGuardSettings(**base)


def test_allowlist_blocks_unknown_when_enabled():
    cfg = _cfg(
        country_mode="allowlist",
        allowed_countries=("CN", "US"),
        block_unknown_country=True,
    )
    d = evaluate_ip_risk(IpIntel(ip="1.1.1.1", country_code="UNKNOWN", risk_score=0), cfg)
    assert d.allow is False
    assert "未知" in d.reason or "允许列表" in d.reason


def test_allowlist_allows_unknown_when_disabled():
    cfg = _cfg(
        country_mode="allowlist",
        allowed_countries=("CN",),
        block_unknown_country=False,
    )
    d = evaluate_ip_risk(IpIntel(ip="1.1.1.1", country_code="UNKNOWN", risk_score=0), cfg)
    assert d.allow is True


def test_allowlist_blocks_country_not_in_list():
    cfg = _cfg(country_mode="allowlist", allowed_countries=("CN",))
    d = evaluate_ip_risk(IpIntel(ip="1.1.1.1", country_code="US", risk_score=0), cfg)
    assert d.allow is False


def test_allowlist_empty_list_no_gate():
    cfg = _cfg(country_mode="allowlist", allowed_countries=())
    d = evaluate_ip_risk(IpIntel(ip="1.1.1.1", country_code="XX", risk_score=0), cfg)
    assert d.allow is True


def test_blacklist_ignores_allowed_list():
    cfg = _cfg(
        country_mode="blacklist",
        allowed_countries=("CN",),  # 黑名单模式下应忽略
        blocked_countries=("RU",),
    )
    d = evaluate_ip_risk(IpIntel(ip="1.1.1.1", country_code="US", risk_score=0), cfg)
    assert d.allow is True


def test_blacklist_blocks_listed():
    cfg = _cfg(country_mode="blacklist", blocked_countries=("RU",))
    d = evaluate_ip_risk(IpIntel(ip="1.1.1.1", country_code="RU", risk_score=0), cfg)
    assert d.allow is False
