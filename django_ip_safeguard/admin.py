from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from django_ip_safeguard.models import IpAccessLog, IpBanRecord, IpGeoPoolStatus, IpGuardPolicy
from django_ip_safeguard.services.policy_service import invalidate_policy_cache


@admin.register(IpGuardPolicy)
class IpGuardPolicyAdmin(ModelAdmin):
    list_display = (
        "name",
        "enabled",
        "risk_score_threshold",
        "rate_limit_per_minute",
        "fail_open",
        "updated_at",
    )
    search_fields = ("name",)
    list_filter_submit = True

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        invalidate_policy_cache()

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        invalidate_policy_cache()


@admin.register(IpGeoPoolStatus)
class IpGeoPoolStatusAdmin(ModelAdmin):
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
class IpAccessLogAdmin(ModelAdmin):
    list_display = ("ip", "country_code", "risk_score", "decision", "path", "created_at")
    search_fields = ("ip", "country_code", "decision", "path")
    list_filter = ("decision", "country_code", "created_at")
    list_filter_submit = True
    readonly_fields = ("ip", "country_code", "risk_score", "risk_tags", "decision", "reason", "path", "created_at")

    def has_add_permission(self, request):
        return False


@admin.register(IpBanRecord)
class IpBanRecordAdmin(ModelAdmin):
    list_display = ("ip", "ban_source", "is_active", "expired_at", "created_at")
    search_fields = ("ip", "ban_reason")
    list_filter = ("is_active", "ban_source", "created_at")
    list_filter_submit = True
    actions = ("mark_active", "mark_inactive")

    @admin.action(description=_("批量设为生效"))
    def mark_active(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description=_("批量设为失效"))
    def mark_inactive(self, request, queryset):
        queryset.update(is_active=False)
