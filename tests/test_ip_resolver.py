from django.http import HttpRequest

from django_ip_safeguard.services.ip_resolver import (
    _in_trusted_proxy,
    _is_valid_ip,
    resolve_client_ip,
)


class TestIsValidIp:
    def test_valid_ipv4(self):
        assert _is_valid_ip("192.168.1.1") is True
        assert _is_valid_ip("10.0.0.1") is True
        assert _is_valid_ip("255.255.255.255") is True

    def test_valid_ipv6(self):
        assert _is_valid_ip("::1") is True
        assert _is_valid_ip("2001:db8::1") is True
        assert _is_valid_ip("fe80::1") is True

    def test_invalid_ip(self):
        assert _is_valid_ip("") is False
        assert _is_valid_ip("invalid") is False
        assert _is_valid_ip("192.168.1.1:8080") is False
        assert _is_valid_ip("192.168.1") is False
        assert _is_valid_ip("256.1.1.1") is False


class TestInTrustedProxy:
    def test_trusted_proxy_match(self):
        assert _in_trusted_proxy("10.0.0.1", ("10.0.0.0/8",)) is True
        assert _in_trusted_proxy("192.168.1.1", ("192.168.0.0/16",)) is True

    def test_trusted_proxy_no_match(self):
        assert _in_trusted_proxy("1.2.3.4", ("10.0.0.0/8",)) is False
        assert _in_trusted_proxy("10.0.0.1", ()) is False

    def test_invalid_remote_addr(self):
        assert _in_trusted_proxy("invalid", ("10.0.0.0/8",)) is False
        assert _in_trusted_proxy("", ("10.0.0.0/8",)) is False


class TestResolveClientIp:
    def _make_request(self, remote_addr, xff=None):
        request = HttpRequest()
        request.META["REMOTE_ADDR"] = remote_addr
        if xff is not None:
            request.META["HTTP_X_FORWARDED_FOR"] = xff
        return request

    def test_direct_connection(self):
        request = self._make_request("1.2.3.4")
        assert resolve_client_ip(request, ()) == "1.2.3.4"

    def test_trusted_proxy_with_xff(self):
        request = self._make_request("10.0.0.1", "1.2.3.4, 10.0.0.2")
        assert resolve_client_ip(request, ("10.0.0.0/8",)) == "1.2.3.4"

    def test_untrusted_proxy_ignores_xff(self):
        request = self._make_request("1.2.3.4", "9.9.9.9")
        # 不信任代理时，使用 REMOTE_ADDR
        assert resolve_client_ip(request, ("10.0.0.0/8",)) == "1.2.3.4"

    def test_invalid_xff_fallback(self):
        request = self._make_request("10.0.0.1", "invalid-ip")
        # XFF 无效时回退到 REMOTE_ADDR
        assert resolve_client_ip(request, ("10.0.0.0/8",)) == "10.0.0.1"

    def test_invalid_remote_addr(self):
        request = self._make_request("invalid")
        assert resolve_client_ip(request, ()) is None

    def test_empty_remote_addr(self):
        request = self._make_request("")
        assert resolve_client_ip(request, ()) is None

    def test_xff_with_port(self):
        request = self._make_request("10.0.0.1", "1.2.3.4:8080")
        # 带端口的 IP 无效，回退到 REMOTE_ADDR
        assert resolve_client_ip(request, ("10.0.0.0/8",)) == "10.0.0.1"
