from django.contrib import admin

from django_ip_safeguard.models import IpAccessLog, IpBanRecord, IpGeoPoolStatus, IpGuardPolicy
from django_ip_safeguard.services.policy_service import invalidate_policy_cache


@admin.register(IpGuardPolicy)
class IpGuardPolicyAdmin(admin.ModelAdmin):
    """IP 策略中心管理。"""

    list_display = (
        "name",
        "enabled",
        "risk_score_threshold",
        "rate_limit_per_minute",
        "fail_open",
        "updated_at",
    )
    search_fields = ("name",)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        invalidate_policy_cache()

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        invalidate_policy_cache()


@admin.register(IpGeoPoolStatus)
class IpGeoPoolStatusAdmin(admin.ModelAdmin):
    """地理 IP 池同步状态（只读运维视图）。"""

    list_display = (
        "pool_key",
        "line_count",
        "v4_interval_count",
        "v6_net_count",
        "last_ok_at",
    )
    readonly_fields = (
        "pool_key",
        "source_url",
        "line_count",
        "v4_interval_count",
        "v6_net_count",
        "last_ok_at",
        "last_error",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(IpAccessLog)
class IpAccessLogAdmin(admin.ModelAdmin):
    """IP 访问日志管理。"""

    list_display = ("ip", "country_code", "risk_score", "decision", "path", "created_at")
    search_fields = ("ip", "country_code", "decision", "path")
    list_filter = ("decision", "country_code", "created_at")
    readonly_fields = ("ip", "country_code", "risk_score", "risk_tags", "decision", "reason", "path", "created_at")

    def has_add_permission(self, request):
        return False


@admin.register(IpBanRecord)
class IpBanRecordAdmin(admin.ModelAdmin):
    """IP 封禁管理。"""

    list_display = ("ip", "ban_source", "is_active", "expired_at", "created_at")
    search_fields = ("ip", "ban_reason")
    list_filter = ("is_active", "ban_source", "created_at")
    actions = ("mark_active", "mark_inactive")

    @admin.action(description="批量设为生效")
    def mark_active(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description="批量设为失效")
    def mark_inactive(self, request, queryset):
        queryset.update(is_active=False)
