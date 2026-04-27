"""验证 settings.IP_GUARD 嵌套字典与扁平 IP_GUARD_* 的合并规则（嵌套为基线，扁平覆盖）。"""

import pytest

from django_ip_safeguard.conf import get_settings


def _del_if_present(settings, name):
    if hasattr(settings, name):
        try:
            delattr(settings, name)
        except (AttributeError, TypeError):
            pass


@pytest.mark.django_db
def test_nested_ip_guard_dict_enabled_and_whitelist(settings):
    _del_if_present(settings, "IP_GUARD_ENABLED")
    _del_if_present(settings, "IP_GUARD_IP_WHITELIST")
    settings.IP_GUARD = {
        "ENABLED": False,
        "WHITELIST_IPS": ["10.0.0.1", "10.0.0.2"],
    }
    cfg = get_settings()
    assert cfg.enabled is False
    assert "10.0.0.1" in cfg.ip_whitelist


@pytest.mark.django_db
def test_flat_ip_guard_overrides_nested(settings):
    settings.IP_GUARD = {"ENABLED": False}
    settings.IP_GUARD_ENABLED = True
    assert get_settings().enabled is True


@pytest.mark.django_db
def test_nested_jwt_ttl_and_secret(settings):
    _del_if_present(settings, "IP_GUARD_JWT_SECRET_KEY")
    _del_if_present(settings, "IP_GUARD_JWT_ACCESS_TTL")
    _del_if_present(settings, "IP_GUARD_JWT_REFRESH_TTL")
    settings.IP_GUARD = {
        "JWT": {
            "SECRET_KEY": "x" * 32,
            "ACCESS_TOKEN_LIFETIME_MINUTES": 45,
            "REFRESH_TOKEN_LIFETIME_DAYS": 14,
        }
    }
    cfg = get_settings()
    assert cfg.jwt_secret_key == "x" * 32
    assert cfg.jwt_access_token_ttl_seconds == 45 * 60
    assert cfg.jwt_refresh_token_ttl_seconds == 14 * 86400


@pytest.mark.django_db
def test_nested_cache_disabled_maps_l1(settings):
    _del_if_present(settings, "IP_GUARD_L1_CACHE_ENABLED")
    settings.IP_GUARD = {
        "CACHE": {"ENABLED": False},
    }
    assert get_settings().l1_cache_enabled is False


@pytest.mark.django_db
def test_nested_redis_url(settings):
    _del_if_present(settings, "IP_GUARD_REDIS_URL")
    settings.IP_GUARD = {
        "REDIS_URL": "redis://custom:6379/2",
    }
    assert get_settings().redis_url == "redis://custom:6379/2"


@pytest.mark.django_db
def test_flat_redis_overrides_nested(settings):
    settings.IP_GUARD = {"REDIS_URL": "redis://nested:6379/0"}
    settings.IP_GUARD_REDIS_URL = "redis://flat:6379/1"
    assert get_settings().redis_url == "redis://flat:6379/1"
