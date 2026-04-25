import ipaddress

from django_ip_safeguard.services.geo_ip_pool_index import build_index_from_text, ip_matches_index


def test_build_index_merges_overlapping_v4():
    text = "10.0.0.0/24\n10.0.0.128/25\n192.168.0.0/16"
    idx = build_index_from_text(text)
    assert idx["line_count"] == 3
    # 10.0.0.0/24 与 10.0.0.128/25 重叠，应合并为一个区间，再加 192.168.0.0/16
    assert len(idx["v4_intervals"]) == 2


def test_ip_matches_v4_and_v6():
    text = "203.0.113.0/32\n2001:db8::/32"
    idx = build_index_from_text(text)
    assert ip_matches_index("203.0.113.0", idx) is True
    assert ip_matches_index("203.0.113.1", idx) is False
    assert ip_matches_index("2001:db8::1", idx) is True


def test_interval_lookup_edge():
    text = "1.1.1.0/24"
    idx = build_index_from_text(text)
    lo = int(ipaddress.ip_address("1.1.1.0"))
    hi = int(ipaddress.ip_address("1.1.1.255"))
    assert ip_matches_index(str(ipaddress.ip_address(lo)), idx)
    assert ip_matches_index(str(ipaddress.ip_address(hi)), idx)
