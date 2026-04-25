from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from django_ip_safeguard.models import (
    IpAccessLog,
    IpBanRecord,
    IpGeoPoolStatus,
    IpGuardPolicy,
    IpReputationHistory,
    ThreatIntelFeedStatus,
)
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
    list_display = ("ip", "country_code", "city", "asn", "risk_score", "decision", "is_datacenter", "created_at")
    search_fields = ("ip", "country_code", "decision", "path", "asn_org")
    list_filter = ("decision", "country_code", "is_datacenter", "is_proxy", "is_tor", "is_vpn", "created_at")
    list_filter_submit = True
    readonly_fields = (
        "ip", "country_code", "country_name", "region", "city",
        "asn", "asn_org", "is_datacenter", "is_proxy", "is_vpn", "is_tor",
        "risk_score", "risk_tags", "decision", "reason", "path", "created_at",
    )

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


@admin.register(IpReputationHistory)
class IpReputationHistoryAdmin(ModelAdmin):
    list_display = ("ip", "country_code", "risk_score", "trend", "block_count_24h", "is_datacenter", "created_at")
    search_fields = ("ip", "country_code")
    list_filter = ("trend", "is_datacenter", "is_proxy", "is_tor", "created_at")
    list_filter_submit = True
    readonly_fields = (
        "ip", "country_code", "asn", "risk_score", "risk_tags",
        "is_datacenter", "is_proxy", "is_vpn", "is_tor",
        "block_count_1h", "allow_count_1h", "block_count_24h", "allow_count_24h",
        "trend", "source", "created_at",
    )

    def has_add_permission(self, request):
        return False


@admin.register(ThreatIntelFeedStatus)
class ThreatIntelFeedStatusAdmin(ModelAdmin):
    list_display = ("feed_name", "threat_type", "auto_ban", "entry_count", "last_ok_at", "enabled")
    search_fields = ("feed_name", "threat_type")
    list_filter = ("enabled", "auto_ban", "threat_type")
    list_filter_submit = True
    readonly_fields = ("entry_count", "auto_ban_count", "last_ok_at", "last_error", "created_at", "updated_at")
