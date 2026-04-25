from django.contrib import admin

from django_ip_safeguard.models import IpAccessLog, IpBanRecord


@admin.register(IpAccessLog)
class IpAccessLogAdmin(admin.ModelAdmin):
    """IP 访问日志管理。"""

    list_display = ("ip", "country_code", "risk_score", "decision", "path", "created_at")
    search_fields = ("ip", "country_code", "decision", "path")
    list_filter = ("decision", "country_code", "created_at")


@admin.register(IpBanRecord)
class IpBanRecordAdmin(admin.ModelAdmin):
    """IP 封禁管理。"""

    list_display = ("ip", "ban_source", "is_active", "expired_at", "created_at")
    search_fields = ("ip", "ban_reason")
    list_filter = ("is_active", "ban_source", "created_at")
