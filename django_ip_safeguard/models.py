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
    """IP 防护策略（支持多策略路由与分级动作）。"""

    ACTION_ALLOW = "allow"
    ACTION_LOG_ONLY = "log_only"
    ACTION_RATE_LIMIT = "rate_limit"
    ACTION_CHALLENGE = "challenge"
    ACTION_BLOCK = "block"
    ACTION_BAN = "ban"
    ACTION_CHOICES = [
        (ACTION_ALLOW, _("放行")),
        (ACTION_LOG_ONLY, _("仅记录")),
        (ACTION_RATE_LIMIT, _("限流")),
        (ACTION_CHALLENGE, _("挑战/二次校验")),
        (ACTION_BLOCK, _("拦截")),
        (ACTION_BAN, _("拦截并封禁")),
    ]

    name = models.CharField(_("策略名"), max_length=64, unique=True, default="default")
    priority = models.IntegerField(
        _("匹配优先级"),
        default=10_000,
        help_text=_("数值越小越优先匹配；default 策略请保持较大值作为兜底"),
    )
    match_host_regex = models.CharField(
        _("Host 正则"),
        max_length=256,
        blank=True,
        default="",
        help_text=_("空表示不限制；匹配 request.get_host() 去掉端口后的主机名"),
    )
    match_path_prefixes = models.JSONField(_("路径前缀列表"), default=list, blank=True)
    match_methods = models.JSONField(
        _("HTTP 方法列表"),
        default=list,
        blank=True,
        help_text=_("空表示任意方法；如 [\"GET\",\"POST\"]"),
    )
    tier_thresholds = models.JSONField(
        _("分级阈值"),
        default=dict,
        blank=True,
        help_text=_('示例 {"medium": 40, "high": 70}；high 缺省时用风险阈值 risk_score_threshold'),
    )
    signal_weights = models.JSONField(
        _("信号权重"),
        default=dict,
        blank=True,
        help_text=_('如 {"risk_score":1.0,"tag_blocked":50}；空则使用内置默认'),
    )
    medium_action = models.CharField(
        _("中风险动作"),
        max_length=32,
        choices=ACTION_CHOICES,
        default=ACTION_BLOCK,
    )
    high_action = models.CharField(
        _("高风险动作"),
        max_length=32,
        choices=ACTION_CHOICES,
        default=ACTION_BAN,
    )
    enabled = models.BooleanField(_("启用防护"), default=True)
    risk_score_threshold = models.IntegerField(_("风险阈值"), default=70)
    blocked_risk_tags = models.JSONField(_("风险标签黑名单"), default=list, blank=True)
    allowed_countries = models.JSONField(_("国家白名单"), default=list, blank=True)
    blocked_countries = models.JSONField(_("国家黑名单"), default=list, blank=True)
    country_mode = models.CharField(
        _("国家/地区策略模式"),
        max_length=24,
        default="default",
        choices=(
            ("default", _("默认（白名单与黑名单同时参与判定）")),
            ("allowlist", _("仅允许列表（仅放行允许列表中的国家）")),
            ("blacklist", _("仅黑名单（只拦截禁止列表中的国家）")),
        ),
        help_text=_("allowlist 下请配置国家白名单；空列表表示不做国家限制。未知国家是否拦截见「未知国家时拦截」。"),
    )
    block_unknown_country = models.BooleanField(
        _("未知国家时拦截"),
        default=True,
        help_text=_("在「仅允许列表」模式下，国家码为空或 UNKNOWN 时是否拦截"),
    )
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
        ordering = ["priority", "name"]


class IpGuardPolicySnapshot(models.Model):
    """策略变更快照，供审计与回滚。"""

    policy = models.ForeignKey(
        IpGuardPolicy,
        on_delete=models.CASCADE,
        related_name="snapshots",
        verbose_name=_("策略"),
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ip_guard_policy_snapshots",
        verbose_name=_("操作人"),
    )
    before_json = models.JSONField(_("变更前"), default=dict, blank=True)
    after_json = models.JSONField(_("变更后"), default=dict, blank=True)
    created_at = models.DateTimeField(_("创建时间"), auto_now_add=True)

    class Meta:
        verbose_name = _("IP策略变更快照")
        verbose_name_plural = _("IP策略变更快照")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["policy", "-created_at"]),
        ]

    def __str__(self):
        return f"Snapshot({self.policy.name} @ {self.created_at})"


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
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ip_guard_access_logs",
        verbose_name=_("访问用户"),
    )
    username = models.CharField(_("用户名快照"), max_length=150, blank=True, default="")
    method = models.CharField(_("HTTP 方法"), max_length=16, blank=True, default="")
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
            models.Index(fields=["user", "-created_at"], name="idx_accesslog_user_created"),
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


class ScheduledTask(models.Model):
    """用户可配置的定时任务模型。"""

    TASK_TYPES = [
        ("geoip2_update", _("GeoIP2 数据库更新")),
        ("threat_intel_sync", _("威胁情报同步")),
        ("ip_reputation_snapshot", _("IP 信誉快照")),
        ("geo_pool_sync", _("地理IP池同步")),
        ("custom", _("自定义命令")),
    ]

    CRON_CHOICES = [
        ("@hourly", _("每小时")),
        ("@daily", _("每天")),
        ("@weekly", _("每周")),
        ("@monthly", _("每月")),
        ("custom", _("自定义")),
    ]

    name = models.CharField(_("任务名称"), max_length=64, unique=True)
    task_type = models.CharField(
        _("任务类型"), max_length=32, choices=TASK_TYPES, default="custom"
    )
    command = models.CharField(
        _("自定义命令"), max_length=255, blank=True,
        help_text=_("自定义管理命令，如 update_geoip2_db --force"),
    )
    cron_expression = models.CharField(
        _("Cron 表达式"), max_length=64, blank=True,
        help_text=_("自定义 Cron 表达式，如 0 3 * * 1（每周一凌晨3点）"),
    )
    cron_preset = models.CharField(
        _("Cron 预设"), max_length=16, choices=CRON_CHOICES, default="@daily",
    )
    interval_minutes = models.PositiveIntegerField(
        _("执行间隔(分钟)"), default=0,
        help_text=_("0 表示使用 Cron 预设或自定义表达式"),
    )
    enabled = models.BooleanField(_("是否启用"), default=True)
    description = models.TextField(_("任务描述"), blank=True, default="")

    last_run_at = models.DateTimeField(_("上次执行时间"), null=True, blank=True)
    last_run_status = models.CharField(_("上次执行状态"), max_length=16, blank=True, default="")
    last_run_output = models.TextField(_("上次执行输出"), blank=True, default="")
    next_run_at = models.DateTimeField(_("下次执行时间"), null=True, blank=True)

    run_count = models.PositiveIntegerField(_("累计执行次数"), default=0)
    success_count = models.PositiveIntegerField(_("成功次数"), default=0)
    failure_count = models.PositiveIntegerField(_("失败次数"), default=0)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_scheduled_tasks",
        verbose_name=_("创建人"),
    )
    created_at = models.DateTimeField(_("创建时间"), auto_now_add=True)
    updated_at = models.DateTimeField(_("更新时间"), auto_now=True)

    class Meta:
        verbose_name = _("定时任务")
        verbose_name_plural = _("定时任务")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_task_type_display()})"

    def get_schedule_display(self) -> str:
        if self.interval_minutes > 0:
            return f"{_('每隔')} {self.interval_minutes} {_('分钟')}"
        if self.cron_preset == "custom":
            if self.cron_expression:
                return f"Cron: {self.cron_expression}"
            return _("未配置")
        return self.get_cron_preset_display()

    def calculate_next_run(self):
        from datetime import timedelta

        from croniter import croniter
        now = timezone.now()

        if self.interval_minutes > 0:
            if self.last_run_at:
                return self.last_run_at + timedelta(minutes=self.interval_minutes)
            return now

        preset_map = {
            "@hourly": "0 * * * *",
            "@daily": "0 0 * * *",
            "@weekly": "0 0 * * 0",
            "@monthly": "0 0 1 * *",
        }

        if self.cron_preset == "custom" and self.cron_expression:
            try:
                cron = croniter(self.cron_expression, now)
                return cron.get_next(type(now))
            except (ValueError, KeyError):
                pass
        elif self.cron_preset in preset_map:
            try:
                cron = croniter(preset_map[self.cron_preset], now)
                return cron.get_next(type(now))
            except (ValueError, KeyError):
                pass

        return None

    def execute(self):
        from io import StringIO

        from django.core.management import call_command

        result = {
            "task": self.name,
            "started_at": timezone.now().isoformat(),
            "status": "unknown",
            "output": "",
            "error": "",
        }

        try:
            output = StringIO()
            command_map = {
                "geoip2_update": "update_geoip2_db",
                "threat_intel_sync": "sync_threat_intel",
                "ip_reputation_snapshot": "snapshot_ip_reputation",
                "geo_pool_sync": "sync_geo_ip_pools",
                "download_geoip2_db": "download_geoip2_db",
            }

            cmd_name = command_map.get(self.task_type, self.task_type)

            if self.task_type == "custom" and self.command:
                parts = self.command.strip().split()
                cmd_name = parts[0] if parts else cmd_name
                args = parts[1:] if len(parts) > 1 else []
            else:
                args = []

            call_command(cmd_name, *args, stdout=output, stderr=output)
            result["status"] = "success"
            result["output"] = output.getvalue()

        except Exception as exc:
            result["status"] = "error"
            result["error"] = str(exc)

        result["completed_at"] = timezone.now().isoformat()
        self._update_execution_result(result)
        return result

    def _update_execution_result(self, result):
        self.last_run_at = timezone.now()
        self.last_run_status = result["status"]
        self.last_run_output = (result.get("output", "") + "\n" + result.get("error", ""))[:2000]
        self.run_count += 1

        if result["status"] == "success":
            self.success_count += 1
        else:
            self.failure_count += 1

        self.next_run_at = self.calculate_next_run()
        self.save(update_fields=[
            "last_run_at", "last_run_status", "last_run_output",
            "run_count", "success_count", "failure_count", "next_run_at", "updated_at",
        ])


class TaskExecutionLog(models.Model):
    """定时任务执行日志。"""

    task = models.ForeignKey(
        ScheduledTask,
        on_delete=models.CASCADE,
        related_name="execution_logs",
        verbose_name=_("定时任务"),
    )
    status = models.CharField(_("执行状态"), max_length=16)
    started_at = models.DateTimeField(_("开始时间"), auto_now_add=True)
    completed_at = models.DateTimeField(_("完成时间"), null=True, blank=True)
    duration_ms = models.PositiveIntegerField(_("执行耗时(毫秒)"), default=0)
    output = models.TextField(_("执行输出"), blank=True, default="")
    error = models.TextField(_("错误信息"), blank=True, default="")

    class Meta:
        verbose_name = _("任务执行日志")
        verbose_name_plural = _("任务执行日志")
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["task", "-started_at"]),
        ]

    def __str__(self):
        return f"{self.task.name} @ {self.started_at.strftime('%Y-%m-%d %H:%M')}"
