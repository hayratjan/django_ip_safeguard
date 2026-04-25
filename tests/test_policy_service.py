from django_ip_safeguard.conf import IpGuardSettings
from django_ip_safeguard.services.policy_service import _POLICY_CACHE, invalidate_policy_cache, load_effective_policy


def test_invalidate_policy_cache():
    _POLICY_CACHE["data"] = {"x": 1}
    _POLICY_CACHE["expires_at"] = 999999999
    invalidate_policy_cache()
    assert _POLICY_CACHE["data"] is None
    assert _POLICY_CACHE["expires_at"] == 0.0


def test_load_effective_policy_fallback_without_db():
    cfg = IpGuardSettings(enable_policy_center=True, policy_cache_seconds=10)
    merged = load_effective_policy(cfg)
    assert merged.enabled == cfg.enabled
