from django.urls import path

from django_ip_safeguard.views import (
    access_log_export_view,
    access_log_list_view,
    auth_me_view,
    csrf_view,
    ban_ip_view,
    ban_list_view,
    dashboard_api_view,
    dashboard_page_view,
    health_view,
    login_view,
    logout_view,
    policy_view,
    unban_ip_view,
)

app_name = "django_ip_safeguard"

urlpatterns = [
    path("", dashboard_page_view, name="dashboard"),
    path("api/auth/csrf/", csrf_view, name="auth_csrf_api"),
    path("api/auth/login/", login_view, name="auth_login_api"),
    path("api/auth/logout/", logout_view, name="auth_logout_api"),
    path("api/auth/me/", auth_me_view, name="auth_me_api"),
    path("api/dashboard/", dashboard_api_view, name="dashboard_api"),
    path("api/policy/", policy_view, name="policy_api"),
    path("api/ban/", ban_ip_view, name="ban_ip_api"),
    path("api/unban/", unban_ip_view, name="unban_ip_api"),
    path("api/ban-list/", ban_list_view, name="ban_list_api"),
    path("api/access-logs/", access_log_list_view, name="access_log_list_api"),
    path("api/access-logs/export/", access_log_export_view, name="access_log_export_api"),
    path("api/health/", health_view, name="health_api"),
]
