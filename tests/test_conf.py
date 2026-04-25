from django_ip_safeguard.conf import IpGuardSettings


def test_default_settings_shape():
    cfg = IpGuardSettings()
    assert isinstance(cfg.enabled, bool)
    assert isinstance(cfg.cache_ttl, int)
    assert cfg.block_status_code == 403
