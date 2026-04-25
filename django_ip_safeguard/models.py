from django.db import models


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
