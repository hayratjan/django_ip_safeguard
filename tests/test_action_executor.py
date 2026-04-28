"""action_executor 单测：根据 Accept 头与 action 选择响应。"""

from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory

from django_ip_safeguard.conf import IpGuardSettings
from django_ip_safeguard.services.action_executor import build_response, is_block_action


def _req(accept: str = "application/json"):
    rf = RequestFactory()
    return rf.get("/x", HTTP_ACCEPT=accept)


def test_allow_returns_none():
    cfg = IpGuardSettings()
    assert build_response(_req(), "allow", "ok", "1.1.1.1", cfg) is None
    assert build_response(_req(), "log_only", "ok", "1.1.1.1", cfg) is None


def test_block_returns_json_with_status_code():
    cfg = IpGuardSettings(block_status_code=403)
    resp = build_response(_req("application/json"), "block", "denied", "1.1.1.1", cfg)
    assert isinstance(resp, JsonResponse)
    assert resp.status_code == 403


def test_rate_limit_uses_429():
    cfg = IpGuardSettings(block_status_code=403)
    resp = build_response(_req("application/json"), "rate_limit", "rl", "1.1.1.1", cfg)
    assert resp.status_code == 429


def test_challenge_uses_challenge_status_code():
    cfg = IpGuardSettings(block_status_code=403, challenge_status_code=418)
    resp = build_response(_req("application/json"), "challenge", "ch", "1.1.1.1", cfg)
    assert resp.status_code == 418


def test_html_branch_when_browser():
    cfg = IpGuardSettings()
    resp = build_response(_req("text/html"), "block", "denied", "1.1.1.1", cfg)
    assert isinstance(resp, HttpResponse) and not isinstance(resp, JsonResponse)
    assert "text/html" in resp["Content-Type"]


def test_is_block_action():
    assert is_block_action("block") is True
    assert is_block_action("ban") is True
    assert is_block_action("allow") is False
    assert is_block_action("log_only") is False
