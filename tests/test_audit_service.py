from django_ip_safeguard.services.audit_service import mask_ip


def test_mask_ipv4_enabled():
    assert mask_ip("192.168.1.100", True, 2) == "192.168.*.*"


def test_mask_ipv4_disabled():
    assert mask_ip("192.168.1.100", False, 2) == "192.168.1.100"


def test_mask_ipv6_enabled():
    masked = mask_ip("2001:db8:85a3:8d3:1319:8a2e:370:7348", True, 2)
    assert masked == "2001:db8:****"
