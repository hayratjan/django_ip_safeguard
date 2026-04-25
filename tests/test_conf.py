from django_ip_safeguard.conf import IpGuardSettings


def test_default_settings_shape():
    cfg = IpGuardSettings()
    assert isinstance(cfg.enabled, bool)
    assert isinstance(cfg.cache_ttl, int)
    assert cfg.block_status_code == 403
    assert cfg.enable_policy_center is True
    assert cfg.provider_circuit_breaker_failures == 5
    assert cfg.high_risk_cache_ttl > cfg.low_risk_cache_ttl
    assert cfg.ip_blacklist == ()
    assert cfg.rate_limit_per_minute == 0
    assert cfg.jwt_algorithm == "HS256"
    assert isinstance(cfg.jwt_access_token_ttl_seconds, int)
    assert isinstance(cfg.jwt_refresh_token_ttl_seconds, int)
    assert cfg.jwt_access_token_ttl_seconds > 0
    assert cfg.jwt_refresh_token_ttl_seconds >= cfg.jwt_access_token_ttl_seconds
