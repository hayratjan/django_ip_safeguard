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
    geo_pools_status_view,
    geo_pools_sync_view,
    health_view,
    jwt_login_view,
    jwt_logout_view,
    jwt_refresh_view,
    login_view,
    logout_view,
    policy_view,
    recent_records_view,
    unban_ip_view,
)

app_name = "django_ip_safeguard"

urlpatterns = [
    path("", dashboard_page_view, name="dashboard"),
    path("api/auth/csrf/", csrf_view, name="auth_csrf_api"),
    path("api/auth/login/", login_view, name="auth_login_api"),
    path("api/auth/jwt/login/", jwt_login_view, name="auth_jwt_login_api"),
    path("api/auth/jwt/refresh/", jwt_refresh_view, name="auth_jwt_refresh_api"),
    path("api/auth/jwt/logout/", jwt_logout_view, name="auth_jwt_logout_api"),
    path("api/auth/logout/", logout_view, name="auth_logout_api"),
    path("api/auth/me/", auth_me_view, name="auth_me_api"),
    path("api/dashboard/", dashboard_api_view, name="dashboard_api"),
    path("api/recent-records/", recent_records_view, name="recent_records_api"),
    path("api/policy/", policy_view, name="policy_api"),
    path("api/geo-pools/status/", geo_pools_status_view, name="geo_pools_status_api"),
    path("api/geo-pools/sync/", geo_pools_sync_view, name="geo_pools_sync_api"),
    path("api/ban/", ban_ip_view, name="ban_ip_api"),
    path("api/unban/", unban_ip_view, name="unban_ip_api"),
    path("api/ban-list/", ban_list_view, name="ban_list_api"),
    path("api/access-logs/", access_log_list_view, name="access_log_list_api"),
    path("api/access-logs/export/", access_log_export_view, name="access_log_export_api"),
    path("api/health/", health_view, name="health_api"),
]
