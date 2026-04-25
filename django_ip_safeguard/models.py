from django.db import models


class IpGuardPolicy(models.Model):
    """IP 防护策略中心（企业版）。"""

    name = models.CharField("策略名", max_length=64, unique=True, default="default")
    enabled = models.BooleanField("启用防护", default=True)
    risk_score_threshold = models.IntegerField("风险阈值", default=70)
    blocked_risk_tags = models.JSONField("风险标签黑名单", default=list, blank=True)
    allowed_countries = models.JSONField("国家白名单", default=list, blank=True)
    blocked_countries = models.JSONField("国家黑名单", default=list, blank=True)
    ip_whitelist = models.JSONField("IP白名单", default=list, blank=True)
    ip_blacklist = models.JSONField("IP黑名单", default=list, blank=True)
    rate_limit_per_minute = models.PositiveIntegerField(
        "单 IP 每分钟请求上限",
        default=0,
        help_text="0 表示不启用；超过则直接拦截（不调用情报接口）",
    )
    fail_open = models.BooleanField("全局失败放行", default=True)
    fail_open_path_prefixes = models.JSONField("按路径失败放行", default=list, blank=True)
    fail_close_path_prefixes = models.JSONField("按路径失败阻断", default=list, blank=True)
    block_status_code = models.IntegerField("拦截状态码", default=403)
    cache_ttl = models.IntegerField("情报缓存TTL", default=3600)
    ban_ttl = models.IntegerField("封禁TTL", default=86400)
    use_db_log = models.BooleanField("记录数据库审计", default=False)
    china_pool_rule = models.CharField(
        "中国内网段池规则",
        max_length=32,
        default="off",
        help_text="off=不启用；allow_only_in_pool=仅允许命中中国内 CIDR 池；block_in_pool=命中中国内池则拦截",
    )
    international_pool_rule = models.CharField(
        "国际网段池规则",
        max_length=32,
        default="off",
        help_text="off=不启用；allow_only_in_pool=仅允许命中国际 CIDR 池；block_in_pool=命中国际池则拦截",
    )
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "IP防护策略"
        verbose_name_plural = "IP防护策略"


class IpGeoPoolStatus(models.Model):
    """地理 IP 池同步状态（与 Redis 中索引对应，便于控制台展示）。"""

    pool_key = models.CharField("池标识", max_length=32, unique=True, db_index=True)
    source_url = models.URLField("数据源 URL", max_length=512, blank=True)
    line_count = models.PositiveIntegerField("原始行数", default=0)
    v4_interval_count = models.PositiveIntegerField("IPv4 合并区间数", default=0)
    v6_net_count = models.PositiveIntegerField("IPv6 网段数", default=0)
    last_ok_at = models.DateTimeField("上次成功同步时间", null=True, blank=True)
    last_error = models.TextField("上次错误信息", blank=True)

    class Meta:
        verbose_name = "地理IP池同步状态"
        verbose_name_plural = "地理IP池同步状态"


class IpAccessLog(models.Model):
    """IP 访问决策日志。"""

    ip = models.GenericIPAddressField("IP")
    country_code = models.CharField("国家码", max_length=16, blank=True)
    risk_score = models.IntegerField("风险分", default=0)
    risk_tags = models.JSONField("风险标签", default=list, blank=True)
    decision = models.CharField("决策", max_length=16, default="allow")
    reason = models.CharField("原因", max_length=255, blank=True)
    path = models.CharField("请求路径", max_length=255, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "IP访问日志"
        verbose_name_plural = "IP访问日志"


class IpBanRecord(models.Model):
    """IP 封禁记录。"""

    ip = models.GenericIPAddressField("IP", unique=True)
    ban_reason = models.CharField("封禁原因", max_length=255)
    ban_source = models.CharField("封禁来源", max_length=32, default="rule")
    expired_at = models.DateTimeField("过期时间", null=True, blank=True)
    is_active = models.BooleanField("是否生效", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "IP封禁记录"
        verbose_name_plural = "IP封禁记录"
