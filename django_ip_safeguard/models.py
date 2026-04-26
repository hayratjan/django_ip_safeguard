import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserProfile(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ip_safeguard_profile",
        verbose_name=_("用户"),
    )
    two_factor_secret = models.CharField(_("2FA密钥"), max_length=64, blank=True, default="")
    two_factor_enabled = models.BooleanField(_("2FA已启用"), default=False)
    language = models.CharField(_("界面语言"), max_length=10, blank=True, default="zh-hans")
    pending_email = models.EmailField(_("待验证邮箱"), blank=True, default="")
    email_verification_token = models.CharField(_("邮箱验证令牌"), max_length=64, blank=True, default="")
    email_token_expires = models.DateTimeField(_("验证令牌过期时间"), null=True, blank=True)
    recovery_codes = models.JSONField(_("2FA恢复码"), default=list, blank=True)
    two_factor_fail_count = models.PositiveIntegerField(_("2FA验证失败次数"), default=0)
    two_factor_locked_until = models.DateTimeField(_("2FA锁定截止时间"), null=True, blank=True)
    password_changed_at = models.DateTimeField(_("密码修改时间"), null=True, blank=True)

    class Meta:
        verbose_name = _("用户安全配置")
        verbose_name_plural = _("用户安全配置")

    def __str__(self):
        return f"Profile({self.user.username})"

    @staticmethod
    def generate_email_token() -> str:
        return secrets.token_urlsafe(32)

    def is_email_token_valid(self) -> bool:
        if not self.email_verification_token or not self.email_token_expires:
            return False
        return timezone.now() < self.email_token_expires

    def is_password_expired(self, max_age_days: int = 0) -> bool:
        if max_age_days <= 0:
            return False
        if not self.password_changed_at:
            return True
        return (timezone.now() - self.password_changed_at).days > max_age_days

    def is_2fa_locked(self) -> bool:
        if self.two_factor_locked_until and timezone.now() < self.two_factor_locked_until:
            return True
        if self.two_factor_locked_until:
            self.two_factor_locked_until = None
            self.two_factor_fail_count = 0
            self.save(update_fields=["two_factor_locked_until", "two_factor_fail_count"])
        return False

    def get_2fa_lock_remaining_seconds(self) -> int:
        if not self.two_factor_locked_until:
            return 0
        remaining = (self.two_factor_locked_until - timezone.now()).total_seconds()
        return max(0, int(remaining))

    def record_2fa_failure(self, lockout_minutes: int = 15, max_failures: int = 5) -> None:
        self.two_factor_fail_count += 1
        if self.two_factor_fail_count >= max_failures:
            self.two_factor_locked_until = timezone.now() + timedelta(minutes=lockout_minutes)
        self.save(update_fields=["two_factor_fail_count", "two_factor_locked_until"])

    def clear_2fa_failure(self) -> None:
        if self.two_factor_fail_count > 0 or self.two_factor_locked_until:
            self.two_factor_fail_count = 0
            self.two_factor_locked_until = None
            self.save(update_fields=["two_factor_fail_count", "two_factor_locked_until"])


class ApiKey(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="api_keys",
        verbose_name=_("用户"),
    )
    name = models.CharField(_("密钥名称"), max_length=64, default="default")
    prefix = models.CharField(_("密钥前缀"), max_length=8, db_index=True)
    key_hash = models.CharField(_("密钥哈希"), max_length=128, unique=True)
    is_active = models.BooleanField(_("是否有效"), default=True)
    expires_at = models.DateTimeField(_("过期时间"), null=True, blank=True)
    last_used_at = models.DateTimeField(_("最后使用时间"), null=True, blank=True)
    created_at = models.DateTimeField(_("创建时间"), auto_now_add=True)
    allowed_ips = models.JSONField(_("允许的IP列表"), default=list, blank=True)
    max_usage = models.IntegerField(_("最大使用次数"), default=0)
    usage_count = models.IntegerField(_("已使用次数"), default=0)
    login_failures = models.IntegerField(_("连续登录失败次数"), default=0)
    last_used_ip = models.GenericIPAddressField(_("最后使用IP"), null=True, blank=True)
    created_by_ip = models.GenericIPAddressField(_("创建时IP"), null=True, blank=True)

    class Meta:
        verbose_name = _("API密钥")
        verbose_name_plural = _("API密钥")
        ordering = ["-created_at"]

    def __str__(self):
        return f"ApiKey({self.user.username}/{self.name}/{self.prefix}...)"

    @staticmethod
    def generate_key() -> tuple:
        raw = f"ipg_{secrets.token_urlsafe(32)}"
        prefix = raw[:8]
        key_hash = hashlib.sha256(raw.encode()).hexdigest()
        return raw, prefix, key_hash

    @staticmethod
    def hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode()).hexdigest()

    def is_valid(self, client_ip: str = None) -> tuple:
        if not self.is_active:
            return False, _("API 密钥已被禁用")
        if self.expires_at and timezone.now() > self.expires_at:
            return False, _("API 密钥已过期")
        if self.max_usage > 0 and self.usage_count >= self.max_usage:
            return False, _("API 密钥已超过最大使用次数")
        if self.allowed_ips and client_ip and client_ip not in self.allowed_ips:
            return False, _("IP 地址不在允许列表中")
        if self.login_failures >= 5:
            return False, _("API 密钥因连续登录失败已被锁定")
        return True, ""


class ApiKeyUsageLog(models.Model):
    api_key = models.ForeignKey(
        ApiKey,
        on_delete=models.CASCADE,
        related_name="usage_logs",
        verbose_name=_("API密钥"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="api_key_usage_logs",
        verbose_name=_("用户"),
    )
    ip = models.GenericIPAddressField(_("IP地址"), null=True, blank=True)
    user_agent = models.TextField(_("User Agent"), blank=True, default="")
    action = models.CharField(_("操作"), max_length=32, default="login")
    success = models.BooleanField(_("是否成功"), default=True)
    failure_reason = models.CharField(_("失败原因"), max_length=128, blank=True, default="")
    created_at = models.DateTimeField(_("创建时间"), auto_now_add=True)

    class Meta:
        verbose_name = _("API密钥使用日志")
        verbose_name_plural = _("API密钥使用日志")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["api_key", "-created_at"]),
        ]

    def __str__(self):
        return f"ApiKeyUsageLog({self.api_key.name}/{self.action}/{self.ip})"


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
    country_name = models.CharField(_("国家名"), max_length=64, blank=True, default="")
    region = models.CharField(_("省份/地区"), max_length=64, blank=True, default="")
    city = models.CharField(_("城市"), max_length=64, blank=True, default="")
    asn = models.IntegerField(_("ASN编号"), null=True, blank=True)
    asn_org = models.CharField(_("ASN组织"), max_length=128, blank=True, default="")
    is_datacenter = models.BooleanField(_("数据中心IP"), default=False)
    is_proxy = models.BooleanField(_("代理IP"), default=False)
    is_vpn = models.BooleanField(_("VPN IP"), default=False)
    is_tor = models.BooleanField(_("Tor出口"), default=False)
    risk_score = models.IntegerField(_("风险分"), default=0)
    risk_tags = models.JSONField(_("风险标签"), default=list, blank=True)
    decision = models.CharField(_("决策"), max_length=16, default="allow")
    reason = models.CharField(_("原因"), max_length=255, blank=True)
    path = models.CharField(_("请求路径"), max_length=255, blank=True)
    created_at = models.DateTimeField(_("创建时间"), auto_now_add=True)

    class Meta:
        verbose_name = _("IP访问日志")
        verbose_name_plural = _("IP访问日志")
        indexes = [
            models.Index(fields=["ip", "-created_at"], name="idx_ip_created"),
            models.Index(fields=["country_code"], name="idx_country"),
            models.Index(fields=["asn"], name="idx_asn"),
            models.Index(fields=["is_datacenter"], name="idx_datacenter"),
            models.Index(fields=["decision", "-created_at"], name="idx_decision_created"),
        ]


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


class IpReputationHistory(models.Model):
    """IP 信誉历史记录：记录 IP 的风险趋势变化。"""

    ip = models.GenericIPAddressField(_("IP"), db_index=True)
    country_code = models.CharField(_("国家码"), max_length=16, blank=True, default="")
    asn = models.IntegerField(_("ASN编号"), null=True, blank=True)
    risk_score = models.IntegerField(_("风险分"), default=0)
    risk_tags = models.JSONField(_("风险标签"), default=list, blank=True)
    is_datacenter = models.BooleanField(_("数据中心"), default=False)
    is_proxy = models.BooleanField(_("代理"), default=False)
    is_vpn = models.BooleanField(_("VPN"), default=False)
    is_tor = models.BooleanField(_("Tor"), default=False)
    block_count_1h = models.PositiveIntegerField(_("近1小时拦截次数"), default=0)
    allow_count_1h = models.PositiveIntegerField(_("近1小时放行次数"), default=0)
    block_count_24h = models.PositiveIntegerField(_("近24小时拦截次数"), default=0)
    allow_count_24h = models.PositiveIntegerField(_("近24小时放行次数"), default=0)
    trend = models.CharField(
        _("趋势"),
        max_length=16,
        default="stable",
        help_text=_("stable=稳定, rising=上升, declining=下降"),
    )
    source = models.CharField(_("数据来源"), max_length=32, default="auto")
    created_at = models.DateTimeField(_("创建时间"), auto_now_add=True)

    class Meta:
        verbose_name = _("IP信誉历史")
        verbose_name_plural = _("IP信誉历史")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["ip", "-created_at"], name="idx_reputation_ip_created"),
            models.Index(fields=["risk_score"], name="idx_reputation_risk"),
            models.Index(fields=["trend"], name="idx_reputation_trend"),
        ]


class ThreatIntelFeedStatus(models.Model):
    """威胁情报源同步状态。"""

    feed_name = models.CharField(_("情报源名称"), max_length=64, unique=True, db_index=True)
    feed_url = models.URLField(_("情报源URL"), max_length=512, blank=True)
    feed_format = models.CharField(_("数据格式"), max_length=16, default="ip_list")
    threat_type = models.CharField(_("威胁类型"), max_length=32, default="unknown")
    auto_ban = models.BooleanField(_("自动封禁"), default=False)
    entry_count = models.PositiveIntegerField(_("条目数"), default=0)
    auto_ban_count = models.PositiveIntegerField(_("自动封禁数"), default=0)
    last_ok_at = models.DateTimeField(_("上次成功同步时间"), null=True, blank=True)
    last_error = models.TextField(_("上次错误信息"), blank=True)
    enabled = models.BooleanField(_("启用"), default=True)
    created_at = models.DateTimeField(_("创建时间"), auto_now_add=True)
    updated_at = models.DateTimeField(_("更新时间"), auto_now=True)

    class Meta:
        verbose_name = _("威胁情报源状态")
        verbose_name_plural = _("威胁情报源状态")
