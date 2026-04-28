# Generated manually for country_mode / access log user fields

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("django_ip_safeguard", "0010_policy_v2"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="ipguardpolicy",
            name="country_mode",
            field=models.CharField(
                choices=[
                    ("default", "默认（白/黑名单均参与加权与兜底）"),
                    ("allowlist", "仅允许列表（列表外及未知可选拦截）"),
                    ("blacklist", "仅黑名单（只拦截禁止列表中的国家）"),
                ],
                default="default",
                help_text="default=与历史一致；allowlist=仅允许 allowed_countries 中的国家；blacklist=仅按 blocked_countries 拦截",
                max_length=24,
                verbose_name="国家/地区策略模式",
            ),
        ),
        migrations.AddField(
            model_name="ipguardpolicy",
            name="block_unknown_country",
            field=models.BooleanField(
                default=True,
                help_text="在「仅允许列表」模式下，国家码为空或 UNKNOWN 时是否拦截",
                verbose_name="未知国家时拦截",
            ),
        ),
        migrations.AddField(
            model_name="ipaccesslog",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="ip_guard_access_logs",
                to=settings.AUTH_USER_MODEL,
                verbose_name="访问用户",
            ),
        ),
        migrations.AddField(
            model_name="ipaccesslog",
            name="username",
            field=models.CharField(blank=True, default="", max_length=150, verbose_name="用户名快照"),
        ),
        migrations.AddField(
            model_name="ipaccesslog",
            name="method",
            field=models.CharField(blank=True, default="", max_length=16, verbose_name="HTTP 方法"),
        ),
        migrations.AddIndex(
            model_name="ipaccesslog",
            index=models.Index(fields=["user", "-created_at"], name="idx_accesslog_user_created"),
        ),
    ]
