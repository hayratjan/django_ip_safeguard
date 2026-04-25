import pytest

from django_ip_safeguard.services.geo_ip_pool_sync import SsrfError, _validate_url


class TestValidateUrl:
    def test_valid_http_url(self):
        _validate_url("http://example.com/list.txt")

    def test_valid_https_url(self):
        _validate_url("https://raw.githubusercontent.com/user/repo/list.txt")

    def test_invalid_scheme(self):
        with pytest.raises(SsrfError, match="不支持的 URL 协议"):
            _validate_url("ftp://example.com/list.txt")

    def test_file_scheme(self):
        with pytest.raises(SsrfError, match="不支持的 URL 协议"):
            _validate_url("file:///etc/passwd")

    def test_localhost(self):
        with pytest.raises(SsrfError, match="禁止访问本地地址"):
            _validate_url("http://localhost/list.txt")

    def test_127_address(self):
        with pytest.raises(SsrfError, match="禁止访问内网地址"):
            _validate_url("http://127.0.0.1/list.txt")

    def test_10_address(self):
        with pytest.raises(SsrfError, match="禁止访问内网地址"):
            _validate_url("http://10.0.0.1/list.txt")

    def test_192_168_address(self):
        with pytest.raises(SsrfError, match="禁止访问内网地址"):
            _validate_url("http://192.168.1.1/list.txt")

    def test_missing_hostname(self):
        with pytest.raises(SsrfError, match="URL 缺少主机名"):
            _validate_url("http:///path")
