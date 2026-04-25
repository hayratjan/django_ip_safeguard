"""JWT 签发、解析与刷新逻辑的单元测试（不依赖真实数据库）。"""

from types import SimpleNamespace
import jwt as pyjwt
import pytest

import django_ip_safeguard.services.jwt_service as jwt_mod
from django_ip_safeguard.conf import IpGuardSettings
from django_ip_safeguard.exceptions import ImproperlyConfiguredError


@pytest.fixture
def jwt_cfg(monkeypatch):
    """固定密钥与 TTL，避免读取未配置的 Django settings。"""
    cfg = IpGuardSettings(
        jwt_secret_key="unit-test-jwt-secret-must-be-long-enough",
        jwt_algorithm="HS256",
        jwt_access_token_ttl_seconds=3600,
        jwt_refresh_token_ttl_seconds=86400,
    )
    monkeypatch.setattr(jwt_mod, "get_settings", lambda: cfg)

    # refresh_access_token / get_user_from_access_token 会调用 ORM，无 Django 配置时用假 User
    class _FakeManager:
        def filter(self, **kwargs):
            self._kwargs = kwargs
            return self

        def first(self):
            pk = self._kwargs.get("pk")
            if pk is None:
                return None
            return SimpleNamespace(id=int(pk), username=f"u{pk}", is_active=True)

    class _FakeUser:
        objects = _FakeManager()

    monkeypatch.setattr(jwt_mod, "get_user_model", lambda: _FakeUser)
    return cfg


def test_issue_token_pair_contains_expected_fields(jwt_cfg):
    user = SimpleNamespace(id=42, username="u42")
    pair = jwt_mod.issue_token_pair(user)
    assert pair["token_type"] == "Bearer"
    assert "access_token" in pair and "refresh_token" in pair
    assert pair["expires_in"] == jwt_cfg.jwt_access_token_ttl_seconds


def test_decode_access_token_payload(jwt_cfg):
    user = SimpleNamespace(id=42, username="u42")
    pair = jwt_mod.issue_token_pair(user)
    pl = jwt_mod.decode_token(pair["access_token"])
    assert pl["typ"] == "access"
    assert pl["sub"] == "42"
    assert pl["username"] == "u42"


def test_refresh_issues_new_access(jwt_cfg):
    user = SimpleNamespace(id=7, username="seven")
    pair = jwt_mod.issue_token_pair(user)
    out = jwt_mod.refresh_access_token(pair["refresh_token"])
    assert out is not None
    pl = jwt_mod.decode_token(out["access_token"])
    assert pl["sub"] == "7"
    assert pl["typ"] == "access"


def test_refresh_rejects_access_token(jwt_cfg):
    user = SimpleNamespace(id=1, username="a")
    pair = jwt_mod.issue_token_pair(user)
    assert jwt_mod.refresh_access_token(pair["access_token"]) is None


def test_decode_rejects_garbage(jwt_cfg):
    with pytest.raises(pyjwt.PyJWTError):
        jwt_mod.decode_token("not-a-valid-jwt")


def test_get_user_from_access_token(jwt_cfg):
    pair = jwt_mod.issue_token_pair(SimpleNamespace(id=99, username="tokuser"))
    u = jwt_mod.get_user_from_access_token(pair["access_token"])
    assert u is not None
    assert u.id == 99
    assert u.username == "u99"


def test_get_user_from_access_token_wrong_typ(jwt_cfg):
    pair = jwt_mod.issue_token_pair(SimpleNamespace(id=1, username="a"))
    assert jwt_mod.get_user_from_access_token(pair["refresh_token"]) is None


def test_issue_token_raises_when_jwt_secret_empty(monkeypatch):
    """未配置密钥时不应静默签发无效 JWT。"""
    cfg = IpGuardSettings(jwt_secret_key="")
    monkeypatch.setattr(jwt_mod, "get_settings", lambda: cfg)
    with pytest.raises(ImproperlyConfiguredError):
        jwt_mod.issue_token_pair(SimpleNamespace(id=1, username="a"))


def test_issue_token_raises_when_jwt_secret_too_short(monkeypatch):
    cfg = IpGuardSettings(jwt_secret_key="short")
    monkeypatch.setattr(jwt_mod, "get_settings", lambda: cfg)
    with pytest.raises(ImproperlyConfiguredError):
        jwt_mod.issue_token_pair(SimpleNamespace(id=1, username="a"))
