from django.urls import path

from django_ip_safeguard.views import (
    dashboard_api_view,
    dashboard_page_view,
    health_view,
    policy_view,
    unban_ip_view,
)

app_name = "django_ip_safeguard"

urlpatterns = [
    path("", dashboard_page_view, name="dashboard"),
    path("api/dashboard/", dashboard_api_view, name="dashboard_api"),
    path("api/policy/", policy_view, name="policy_api"),
    path("api/unban/", unban_ip_view, name="unban_ip_api"),
    path("api/health/", health_view, name="health_api"),
]
