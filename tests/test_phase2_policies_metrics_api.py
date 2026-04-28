"""阶段二 API：/api/metrics/、/api/policies/、快照列表与回滚（基于 Django 测试客户端）。"""

import json

import pytest
from django.contrib.auth.models import Permission, User

from django_ip_safeguard.models import IpGuardPolicy, IpGuardPolicySnapshot


def _grant(u, codename: str):
    p = Permission.objects.get(codename=codename, content_type__app_label="django_ip_safeguard")
    u.user_permissions.add(p)


@pytest.mark.django_db
def test_metrics_api_ok():
    u = User.objects.create_user("m1", password="testpass12", is_staff=True)
    _grant(u, "view_ipguardpolicy")
    from django.test import Client

    c = Client()
    c.force_login(u)
    r = c.get("/ip-guard/api/metrics/")
    assert r.status_code == 200
    body = r.json()
    assert body.get("code") == 0
    assert "redis_counters" in body.get("data", {})
    assert "in_process_summary" in body.get("data", {})


@pytest.mark.django_db
def test_policies_list_and_create():
    u = User.objects.create_user("p1", password="testpass12", is_staff=True)
    _grant(u, "view_ipguardpolicy")
    _grant(u, "change_ipguardpolicy")
    from django.test import Client

    c = Client()
    c.force_login(u)
    r = c.get("/ip-guard/api/policies/")
    assert r.status_code == 200
    assert r.json().get("code") == 0

    c.get("/ip-guard/api/auth/csrf/")
    tok = c.cookies.get("csrftoken").value
    r2 = c.post(
        "/ip-guard/api/policies/",
        data=json.dumps({"name": "apitest-policy"}),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=tok,
    )
    assert r2.status_code == 200
    assert IpGuardPolicy.objects.filter(name="apitest-policy").exists()


@pytest.mark.django_db
def test_policy_snapshot_list_and_rollback():
    u = User.objects.create_user("rb", password="testpass12", is_staff=True)
    _grant(u, "view_ipguardpolicy")
    _grant(u, "change_ipguardpolicy")
    pol, _ = IpGuardPolicy.objects.get_or_create(name="default")
    pol.risk_score_threshold = 71
    pol.save()
    snap = IpGuardPolicySnapshot.objects.create(
        policy=pol,
        actor=u,
        before_json={"risk_score_threshold": 70},
        after_json={"risk_score_threshold": 71},
    )
    from django.test import Client

    c = Client()
    c.force_login(u)
    r = c.get("/ip-guard/api/policy/snapshots/")
    assert r.status_code == 200
    items = r.json().get("data", {}).get("items", [])
    assert any(x.get("id") == snap.id for x in items)

    c.get("/ip-guard/api/auth/csrf/")
    tok = c.cookies.get("csrftoken").value
    r3 = c.post(
        f"/ip-guard/api/policy/snapshots/{snap.id}/rollback/",
        data=json.dumps({}),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=tok,
    )
    assert r3.status_code == 200
    pol.refresh_from_db()
    assert pol.risk_score_threshold == 70


@pytest.mark.django_db
def test_policy_snapshot_before_after_payload_order():
    """保存策略时 before_json 应为变更前、after_json 为变更后。"""
    u = User.objects.create_user("ord", password="testpass12", is_staff=True)
    _grant(u, "view_ipguardpolicy")
    _grant(u, "change_ipguardpolicy")
    pol, _ = IpGuardPolicy.objects.get_or_create(name="default")
    pol.risk_score_threshold = 50
    pol.save()
    from django.test import Client

    c = Client()
    c.force_login(u)
    c.get("/ip-guard/api/auth/csrf/")
    tok = c.cookies.get("csrftoken").value
    c.post(
        "/ip-guard/api/policy/",
        data=json.dumps({"risk_score_threshold": 88}),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=tok,
    )
    snap = IpGuardPolicySnapshot.objects.filter(policy=pol).order_by("-id").first()
    assert snap is not None
    assert snap.before_json.get("risk_score_threshold") == 50
    assert snap.after_json.get("risk_score_threshold") == 88
