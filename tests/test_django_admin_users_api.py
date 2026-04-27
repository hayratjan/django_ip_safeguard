import json

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client


@pytest.mark.django_db
def test_admin_users_list_forbidden_without_perm():
    u = User.objects.create_user("staff1", password="testpass12", is_staff=True)
    client = Client()
    client.force_login(u)
    resp = client.get("/ip-guard/api/admin/users/")
    assert resp.status_code == 403
    body = resp.json()
    assert body.get("code") == 4031


@pytest.mark.django_db
def test_admin_users_list_ok_for_superuser():
    User.objects.create_user("staff1", password="testpass12", is_staff=True)
    admin = User.objects.create_user("su", password="testpass12", is_staff=True, is_superuser=True)
    client = Client()
    client.force_login(admin)
    resp = client.get("/ip-guard/api/admin/users/")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("code") == 0
    assert "items" in body.get("data", {})
    assert body["data"]["pagination"]["total"] >= 2


@pytest.mark.django_db
def test_admin_users_list_ok_with_view_user_perm():
    u = User.objects.create_user("viewer", password="testpass12", is_staff=True)
    perm = Permission.objects.get(codename="view_user", content_type__app_label="auth")
    u.user_permissions.add(perm)
    client = Client()
    client.force_login(u)
    resp = client.get("/ip-guard/api/admin/users/")
    assert resp.status_code == 200
    assert resp.json().get("code") == 0


@pytest.mark.django_db
def test_admin_groups_list_requires_view_user():
    u = User.objects.create_user("nog", password="testpass12", is_staff=True)
    client = Client()
    client.force_login(u)
    resp = client.get("/ip-guard/api/admin/groups/")
    assert resp.status_code == 403
    assert resp.json().get("code") == 4031


@pytest.mark.django_db
def test_admin_user_create_superuser_only_flag():
    actor = User.objects.create_user("actor", password="testpass12", is_staff=True)
    perm_add = Permission.objects.get(codename="add_user", content_type__app_label="auth")
    perm_view = Permission.objects.get(codename="view_user", content_type__app_label="auth")
    actor.user_permissions.add(perm_add, perm_view)
    client = Client()
    client.force_login(actor)
    client.get("/ip-guard/api/auth/csrf/")
    token = client.cookies.get("csrftoken").value
    resp = client.post(
        "/ip-guard/api/admin/users/",
        data=json.dumps(
            {
                "username": "newu1",
                "password": "longpass12",
                "is_superuser": True,
            }
        ),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert resp.json().get("code") == 4032


@pytest.mark.django_db
def test_admin_user_create_ok():
    admin = User.objects.create_user("root2", password="testpass12", is_staff=True, is_superuser=True)
    client = Client()
    client.force_login(admin)
    client.get("/ip-guard/api/auth/csrf/")
    token = client.cookies.get("csrftoken").value
    resp = client.post(
        "/ip-guard/api/admin/users/",
        data=json.dumps(
            {
                "username": "newstaff",
                "password": "longpass12",
                "is_staff": True,
            }
        ),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert resp.status_code == 200
    assert resp.json().get("code") == 0
    assert User.objects.filter(username="newstaff").exists()


@pytest.mark.django_db
def test_admin_user_patch_cannot_disable_self():
    u = User.objects.create_user("self1", password="testpass12", is_staff=True, is_superuser=True)
    client = Client()
    client.force_login(u)
    client.get("/ip-guard/api/auth/csrf/")
    token = client.cookies.get("csrftoken").value
    resp = client.patch(
        f"/ip-guard/api/admin/users/{u.pk}/",
        data=json.dumps({"is_active": False}),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert resp.json().get("code") == 4005
