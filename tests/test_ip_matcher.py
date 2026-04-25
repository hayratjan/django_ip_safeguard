from django_ip_safeguard.services.ip_matcher import first_matching_rule, ip_matches_rule


def test_exact_ipv4_match():
    assert ip_matches_rule("192.168.1.10", "192.168.1.10") is True
    assert ip_matches_rule("192.168.1.11", "192.168.1.10") is False


def test_cidr_ipv4_contains():
    assert ip_matches_rule("10.0.0.5", "10.0.0.0/24") is True
    assert ip_matches_rule("10.0.1.5", "10.0.0.0/24") is False


def test_first_matching_rule_order():
    hit, rule = first_matching_rule("203.0.113.9", ["203.0.113.0/28", "203.0.113.9"])
    assert hit is True
    assert rule == "203.0.113.0/28"


def test_ipv6_cidr():
    assert ip_matches_rule("2001:db8::1", "2001:db8::/32") is True
