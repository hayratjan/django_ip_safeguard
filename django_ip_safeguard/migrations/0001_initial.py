from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="IpAccessLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ip", models.GenericIPAddressField(verbose_name="IP")),
                ("country_code", models.CharField(blank=True, max_length=16, verbose_name="国家码")),
                ("risk_score", models.IntegerField(default=0, verbose_name="风险分")),
                ("risk_tags", models.JSONField(blank=True, default=list, verbose_name="风险标签")),
                ("decision", models.CharField(default="allow", max_length=16, verbose_name="决策")),
                ("reason", models.CharField(blank=True, max_length=255, verbose_name="原因")),
                ("path", models.CharField(blank=True, max_length=255, verbose_name="请求路径")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
            ],
            options={"verbose_name": "IP访问日志", "verbose_name_plural": "IP访问日志"},
        ),
        migrations.CreateModel(
            name="IpBanRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ip", models.GenericIPAddressField(unique=True, verbose_name="IP")),
                ("ban_reason", models.CharField(max_length=255, verbose_name="封禁原因")),
                ("ban_source", models.CharField(default="rule", max_length=32, verbose_name="封禁来源")),
                ("expired_at", models.DateTimeField(blank=True, null=True, verbose_name="过期时间")),
                ("is_active", models.BooleanField(default=True, verbose_name="是否生效")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
            ],
            options={"verbose_name": "IP封禁记录", "verbose_name_plural": "IP封禁记录"},
        ),
        migrations.CreateModel(
            name="IpGuardPolicy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(default="default", max_length=64, unique=True, verbose_name="策略名")),
                ("enabled", models.BooleanField(default=True, verbose_name="启用防护")),
                ("risk_score_threshold", models.IntegerField(default=70, verbose_name="风险阈值")),
                ("blocked_risk_tags", models.JSONField(blank=True, default=list, verbose_name="风险标签黑名单")),
                ("allowed_countries", models.JSONField(blank=True, default=list, verbose_name="国家白名单")),
                ("blocked_countries", models.JSONField(blank=True, default=list, verbose_name="国家黑名单")),
                ("ip_whitelist", models.JSONField(blank=True, default=list, verbose_name="IP白名单")),
                ("fail_open", models.BooleanField(default=True, verbose_name="全局失败放行")),
                ("fail_open_path_prefixes", models.JSONField(blank=True, default=list, verbose_name="按路径失败放行")),
                ("fail_close_path_prefixes", models.JSONField(blank=True, default=list, verbose_name="按路径失败阻断")),
                ("block_status_code", models.IntegerField(default=403, verbose_name="拦截状态码")),
                ("cache_ttl", models.IntegerField(default=3600, verbose_name="情报缓存TTL")),
                ("ban_ttl", models.IntegerField(default=86400, verbose_name="封禁TTL")),
                ("use_db_log", models.BooleanField(default=False, verbose_name="记录数据库审计")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
            ],
            options={"verbose_name": "IP防护策略", "verbose_name_plural": "IP防护策略"},
        ),
    ]
