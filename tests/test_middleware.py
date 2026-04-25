from django_ip_safeguard.middleware import should_fail_open


def test_should_fail_open_by_default_value():
    result = should_fail_open("/api/data", True, (), ())
    assert result is True


def test_should_fail_close_when_path_matches_close_prefix():
    result = should_fail_open(
        "/api/login",
        True,
        open_prefixes=("/public",),
        close_prefixes=("/api/login", "/api/pay"),
    )
    assert result is False


def test_should_fail_open_when_path_matches_open_prefix():
    result = should_fail_open(
        "/public/home",
        False,
        open_prefixes=("/public",),
        close_prefixes=("/secure",),
    )
    assert result is True
