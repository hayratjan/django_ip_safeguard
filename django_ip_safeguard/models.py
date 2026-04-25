from django.db import models
from django.utils.translation import gettext_lazy as _


class IpGuardPolicy(models.Model):

    name = models.CharField(_("策略名"), max_length=64, unique=True, default="default")
    enabled = models.BooleanField(_("启用防护"), default=True)
    risk_score_threshold = models.IntegerField(_("风险阈值"), default=70)
    blocked_risk_tags = models.JSONField(_("风险标签黑名单"), default=list, blank=True)
    allowed_countries = models.JSONField(_("国家白名单"), default=list, blank=True)
    blocked_countries = models.JSONField(_("国家黑名单"), default=list, blank=True)
    ip_whitelist = models.JSONField(_("IP白名单"), default=list, blank=True)
    ip_blacklist = models.JSONField(_("IP黑名单"), default=list, blank=True)
    rate_limit_per_minute = models.PositiveIntegerField(
        _("单 IP 每分钟请求上限"),
        default=0,
        help_text=_("0 表示不启用；超过则直接拦截（不调用情报接口）"),
    )
    fail_open = models.BooleanField(_("全局失败放行"), default=True)
    fail_open_path_prefixes = models.JSONField(_("按路径失败放行"), default=list, blank=True)
    fail_close_path_prefixes = models.JSONField(_("按路径失败阻断"), default=list, blank=True)
    block_status_code = models.IntegerField(_("拦截状态码"), default=403)
    cache_ttl = models.IntegerField(_("情报缓存TTL"), default=3600)
    ban_ttl = models.IntegerField(_("封禁TTL"), default=86400)
    use_db_log = models.BooleanField(_("记录数据库审计"), default=False)
    china_pool_rule = models.CharField(
        _("中国内网段池规则"),
        max_length=32,
        default="off",
        help_text=_("off=不启用；allow_only_in_pool=仅允许命中中国内 CIDR 池；block_in_pool=命中中国内池则拦截"),
    )
    international_pool_rule = models.CharField(
        _("国际网段池规则"),
        max_length=32,
        default="off",
        help_text=_("off=不启用；allow_only_in_pool=仅允许命中国际 CIDR 池；block_in_pool=命中国际池则拦截"),
    )
    updated_at = models.DateTimeField(_("更新时间"), auto_now=True)

    class Meta:
        verbose_name = _("IP防护策略")
        verbose_name_plural = _("IP防护策略")


class IpGeoPoolStatus(models.Model):

    pool_key = models.CharField(_("池标识"), max_length=32, unique=True, db_index=True)
    source_url = models.URLField(_("数据源 URL"), max_length=512, blank=True)
    line_count = models.PositiveIntegerField(_("原始行数"), default=0)
    v4_interval_count = models.PositiveIntegerField(_("IPv4 合并区间数"), default=0)
    v6_net_count = models.PositiveIntegerField(_("IPv6 网段数"), default=0)
    last_ok_at = models.DateTimeField(_("上次成功同步时间"), null=True, blank=True)
    last_error = models.TextField(_("上次错误信息"), blank=True)

    class Meta:
        verbose_name = _("地理IP池同步状态")
        verbose_name_plural = _("地理IP池同步状态")


class IpAccessLog(models.Model):

    ip = models.GenericIPAddressField(_("IP"))
    country_code = models.CharField(_("国家码"), max_length=16, blank=True)
    risk_score = models.IntegerField(_("风险分"), default=0)
    risk_tags = models.JSONField(_("风险标签"), default=list, blank=True)
    decision = models.CharField(_("决策"), max_length=16, default="allow")
    reason = models.CharField(_("原因"), max_length=255, blank=True)
    path = models.CharField(_("请求路径"), max_length=255, blank=True)
    created_at = models.DateTimeField(_("创建时间"), auto_now_add=True)

    class Meta:
        verbose_name = _("IP访问日志")
        verbose_name_plural = _("IP访问日志")


class IpBanRecord(models.Model):

    ip = models.GenericIPAddressField(_("IP"), unique=True)
    ban_reason = models.CharField(_("封禁原因"), max_length=255)
    ban_source = models.CharField(_("封禁来源"), max_length=32, default="rule")
    expired_at = models.DateTimeField(_("过期时间"), null=True, blank=True)
    is_active = models.BooleanField(_("是否生效"), default=True)
    created_at = models.DateTimeField(_("创建时间"), auto_now_add=True)

    class Meta:
        verbose_name = _("IP封禁记录")
        verbose_name_plural = _("IP封禁记录")
