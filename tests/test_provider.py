from django_ip_safeguard.conf import IpGuardSettings
from django_ip_safeguard.services.provider_factory import build_provider
from django_ip_safeguard.services.provider_http import DummyIpIntelProvider, HttpIpIntelProvider


def test_build_dummy_provider():
    provider = build_provider(IpGuardSettings(provider="dummy"))
    assert isinstance(provider, DummyIpIntelProvider)


def test_build_http_provider():
    provider = build_provider(
        IpGuardSettings(
            provider="http",
            provider_endpoint="https://example.com/ip-intel",
            provider_api_key="abc",
            provider_timeout=2.5,
            provider_headers={"X-App": "ip-guard"},
        )
    )
    assert isinstance(provider, HttpIpIntelProvider)
    assert provider.endpoint == "https://example.com/ip-intel"
    assert provider.api_key == "abc"
    assert provider.max_retries == 2


def test_http_provider_parse_payload(monkeypatch):
    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"country_code": "cn", "risk_score": 88, "risk_tags": ["vpn"]}

    class _Client:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def get(self, endpoint, params, headers):
            assert endpoint == "https://example.com/ip-intel"
            assert params["ip"] == "8.8.8.8"
            assert "Authorization" in headers
            return _Resp()

    monkeypatch.setattr("django_ip_safeguard.services.provider_http.httpx.Client", _Client)

    provider = HttpIpIntelProvider(
        endpoint="https://example.com/ip-intel",
        api_key="k1",
        timeout=3.0,
        headers={},
    )
    intel = provider.fetch_ip_intel("8.8.8.8")

    assert intel.country_code == "CN"
    assert intel.risk_score == 88
    assert intel.risk_tags == ["vpn"]


def test_http_provider_retry_success(monkeypatch):
    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"country_code": "SG", "risk_score": 10, "risk_tags": []}

    call_state = {"count": 0}

    class _Client:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def get(self, endpoint, params, headers):
            call_state["count"] += 1
            if call_state["count"] == 1:
                raise RuntimeError("temporary error")
            return _Resp()

    monkeypatch.setattr("django_ip_safeguard.services.provider_http.httpx.Client", _Client)
    monkeypatch.setattr("django_ip_safeguard.services.provider_http.time.sleep", lambda _: None)

    provider = HttpIpIntelProvider(
        endpoint="https://example.com/ip-intel",
        api_key="k1",
        timeout=3.0,
        max_retries=1,
        retry_backoff=0.01,
    )
    intel = provider.fetch_ip_intel("8.8.4.4")
    assert call_state["count"] == 2
    assert intel.country_code == "SG"
