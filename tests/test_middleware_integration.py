"""中间件集成测试：用 RequestFactory + 假 provider/redis 跑核心分支。

为不依赖真实 Redis：
- patch ``redis.Redis.from_url`` → :class:`FakeRedis`
- patch ``policy_service.start_policy_invalidate_subscriber`` 为空
- patch ``provider_factory.build_provider`` 为可控 stub
- patch ``load_effective_policy`` 直接返回构造好的 ``IpGuardSettings``
"""

import json
from dataclasses import replace

import pytest
from django.test import RequestFactory

from tests.test_cache_service import FakeRedis


class _StubProvider:
    def __init__(self, intel):
        self._intel = intel

    def fetch_ip_intel(self, ip):
        return replace(self._intel, ip=ip)


class _Pass:
    status_code = 200
    headers = {"Content-Type": "text/plain"}

    def __getitem__(self, item):
        return self.headers.get(item, "")


@pytest.fixture()
def make_middleware(monkeypatch):
    """工厂：返回 ``build(config_overrides) -> middleware``。"""
    fake = FakeRedis()
    monkeypatch.setattr(
        "django_ip_safeguard.services.cache.redis.Redis.from_url",
        lambda *a, **kw: fake,
    )
    monkeypatch.setattr(
        "django_ip_safeguard.middleware.start_policy_invalidate_subscriber",
        lambda url: None,
    )

    from django_ip_safeguard.types import IpIntel

    clean_intel = IpIntel(ip="2.2.2.2", country_code="CN", risk_score=10, risk_tags=[])
    monkeypatch.setattr(
        "django_ip_safeguard.middleware.build_provider",
        lambda cfg: _StubProvider(clean_intel),
    )

    from django_ip_safeguard.middleware import IpGuardMiddleware

    def _build(**overrides):
        from django_ip_safeguard.conf import get_settings

        base = get_settings()
        runtime = replace(base, enable_policy_center=False, **overrides)
        # 直接覆盖 load_effective_policy 返回值
        monkeypatch.setattr(
            "django_ip_safeguard.middleware.load_effective_policy",
            lambda cfg, request=None: runtime,
        )
        mw = IpGuardMiddleware(get_response=lambda req: _Pass())
        # 中间件内部已通过 load_effective_policy 拿配置；为 skip_path_prefixes 这种最早期判断，
        # 需要把 config 也换成 runtime（构造时的 self.config 仍是原始）。
        object.__setattr__(mw, "config", runtime)
        return mw

    return _build


def test_skip_path_prefix_bypasses(make_middleware):
    mw = make_middleware(skip_path_prefixes=("/healthz",))
    rf = RequestFactory()
    resp = mw(rf.get("/healthz/ping", REMOTE_ADDR="9.9.9.9"))
    assert resp.status_code == 200


def test_blacklist_returns_block(make_middleware):
    mw = make_middleware(ip_blacklist=("9.9.9.9",))
    rf = RequestFactory()
    resp = mw(rf.get("/api/x", REMOTE_ADDR="9.9.9.9", HTTP_ACCEPT="application/json"))
    assert resp.status_code == mw.config.block_status_code
    body = json.loads(resp.content.decode())
    assert body["ip"] == "9.9.9.9"
    assert body.get("action") == "block"


def test_whitelist_passes(make_middleware):
    mw = make_middleware(ip_whitelist=("9.9.9.9",))
    rf = RequestFactory()
    resp = mw(rf.get("/api/x", REMOTE_ADDR="9.9.9.9"))
    assert resp.status_code == 200


def test_clean_ip_passes_through_provider(make_middleware):
    mw = make_middleware()
    rf = RequestFactory()
    resp = mw(rf.get("/api/x", REMOTE_ADDR="2.2.2.2"))
    assert resp.status_code == 200


def test_html_accept_returns_html_block(make_middleware):
    mw = make_middleware(ip_blacklist=("9.9.9.9",))
    rf = RequestFactory()
    resp = mw(rf.get("/x", REMOTE_ADDR="9.9.9.9", HTTP_ACCEPT="text/html"))
    assert resp.status_code == mw.config.block_status_code
    assert "text/html" in resp["Content-Type"]
