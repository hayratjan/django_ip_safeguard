from django_ip_safeguard.services.provider_chain import ChainedProvider
from django_ip_safeguard.services.provider_http import DummyIpIntelProvider
from django_ip_safeguard.services.asn_lookup import AsnLookupService
from django_ip_safeguard.types import IpIntel


def test_chained_provider_first_success():
    provider = ChainedProvider(
        providers=[DummyIpIntelProvider()],
        merge_results=False,
    )
    intel = provider.fetch_ip_intel("8.8.8.8")
    assert intel.ip == "8.8.8.8"


def test_chained_provider_merge():
    class Provider1:
        def fetch_ip_intel(self, ip):
            return IpIntel(ip=ip, country_code="US", risk_score=30, source="p1")

    class Provider2:
        def fetch_ip_intel(self, ip):
            return IpIntel(ip=ip, city="Mountain View", asn=15169, source="p2")

    provider = ChainedProvider(
        providers=[Provider1(), Provider2()],
        merge_results=True,
    )
    intel = provider.fetch_ip_intel("8.8.8.8")
    assert intel.country_code == "US"
    assert intel.city == "Mountain View"
    assert intel.asn == 15169
    assert "p1" in intel.source
    assert "p2" in intel.source


def test_chained_provider_fallback():
    class FailingProvider:
        def fetch_ip_intel(self, ip):
            raise RuntimeError("fail")

    provider = ChainedProvider(
        providers=[FailingProvider(), DummyIpIntelProvider()],
        merge_results=False,
    )
    intel = provider.fetch_ip_intel("8.8.8.8")
    assert intel.ip == "8.8.8.8"


def test_chained_provider_empty():
    provider = ChainedProvider(providers=[], merge_results=True)
    intel = provider.fetch_ip_intel("8.8.8.8")
    assert intel.ip == "8.8.8.8"
    assert intel.source == "empty_chain"


def test_asn_lookup_datacenter():
    service = AsnLookupService()
    assert service.is_datacenter(16509) is True
    assert service.is_datacenter(37963) is True
    assert service.is_datacenter(12345) is False


def test_asn_lookup_cdn():
    service = AsnLookupService()
    assert service.is_cdn(13335) is True
    assert service.is_cdn(15169) is True
    assert service.is_cdn(99999) is False


def test_asn_lookup_enrich():
    service = AsnLookupService()
    intel = IpIntel(ip="8.8.8.8", asn=16509)
    service.enrich_ip_intel(intel)
    assert intel.is_datacenter is True
    assert "cdn" in intel.risk_tags


def test_asn_lookup_enrich_no_asn():
    service = AsnLookupService()
    intel = IpIntel(ip="1.2.3.4")
    service.enrich_ip_intel(intel)
    assert intel.is_datacenter is False


def test_asn_lookup_org_name():
    service = AsnLookupService()
    assert "Amazon" in service.get_org_name(16509)
    assert service.get_org_name(None) == ""
    assert service.get_org_name(99999) == ""
