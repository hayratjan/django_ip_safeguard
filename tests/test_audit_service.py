from django_ip_safeguard.services.audit_service import mask_ip, log_access_decision
from django_ip_safeguard.types import IpIntel


def test_mask_ipv4_enabled():
    assert mask_ip("192.168.1.100", True, 2) == "192.168.*.*"


def test_mask_ipv4_disabled():
    assert mask_ip("192.168.1.100", False, 2) == "192.168.1.100"


def test_mask_ipv6_enabled():
    masked = mask_ip("2001:db8:85a3:8d3:1319:8a2e:370:7348", True, 2)
    assert masked == "2001:db8:****"


def test_mask_ipv4_keep_prefix_1():
    assert mask_ip("10.20.30.40", True, 1) == "10.*.*.*"


def test_mask_ipv4_keep_prefix_3():
    assert mask_ip("10.20.30.40", True, 3) == "10.20.30.*"


def test_mask_ipv6_disabled():
    ip = "2001:db8:85a3:8d3:1319:8a2e:370:7348"
    assert mask_ip(ip, False, 2) == ip


def test_log_access_stores_full_ip(db, settings):
    settings.IP_GUARD_USE_DB_LOG = True
    ip_intel = IpIntel(ip="192.168.1.100", country_code="CN", risk_score=50, risk_tags=[], source="test")
    log_access_decision(
        enabled=True,
        ip="192.168.1.100",
        path="/test/",
        decision="allow",
        reason="test",
        ip_intel=ip_intel,
        ip_mask_enabled=True,
        ip_mask_keep_prefix=2,
    )
    from django_ip_safeguard.models import IpAccessLog
    log = IpAccessLog.objects.first()
    assert log is not None
    assert log.ip == "192.168.1.100"


def test_log_access_stores_full_ip_when_mask_disabled(db, settings):
    settings.IP_GUARD_USE_DB_LOG = True
    ip_intel = IpIntel(ip="10.0.0.1", country_code="US", risk_score=10, risk_tags=[], source="test")
    log_access_decision(
        enabled=True,
        ip="10.0.0.1",
        path="/api/",
        decision="allow",
        reason="whitelist",
        ip_intel=ip_intel,
        ip_mask_enabled=False,
        ip_mask_keep_prefix=2,
    )
    from django_ip_safeguard.models import IpAccessLog
    log = IpAccessLog.objects.first()
    assert log is not None
    assert log.ip == "10.0.0.1"
