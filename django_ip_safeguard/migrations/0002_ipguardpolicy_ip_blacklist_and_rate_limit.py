from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("django_ip_safeguard", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="ipguardpolicy",
            name="ip_blacklist",
            field=models.JSONField(blank=True, default=list, verbose_name="IP黑名单"),
        ),
        migrations.AddField(
            model_name="ipguardpolicy",
            name="rate_limit_per_minute",
            field=models.PositiveIntegerField(
                default=0,
                help_text="0 表示不启用；超过则直接拦截（不调用情报接口）",
                verbose_name="单 IP 每分钟请求上限",
            ),
        ),
    ]
