from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("django_ip_safeguard", "0002_ipguardpolicy_ip_blacklist_and_rate_limit"),
    ]

    operations = [
        migrations.AddField(
            model_name="ipguardpolicy",
            name="china_pool_rule",
            field=models.CharField(
                default="off",
                help_text="off=不启用；allow_only_in_pool=仅允许命中中国内 CIDR 池；block_in_pool=命中中国内池则拦截",
                max_length=32,
                verbose_name="中国内网段池规则",
            ),
        ),
        migrations.AddField(
            model_name="ipguardpolicy",
            name="international_pool_rule",
            field=models.CharField(
                default="off",
                help_text="off=不启用；allow_only_in_pool=仅允许命中国际 CIDR 池；block_in_pool=命中国际池则拦截",
                max_length=32,
                verbose_name="国际网段池规则",
            ),
        ),
        migrations.CreateModel(
            name="IpGeoPoolStatus",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("pool_key", models.CharField(db_index=True, max_length=32, unique=True, verbose_name="池标识")),
                ("source_url", models.URLField(blank=True, max_length=512, verbose_name="数据源 URL")),
                ("line_count", models.PositiveIntegerField(default=0, verbose_name="原始行数")),
                ("v4_interval_count", models.PositiveIntegerField(default=0, verbose_name="IPv4 合并区间数")),
                ("v6_net_count", models.PositiveIntegerField(default=0, verbose_name="IPv6 网段数")),
                ("last_ok_at", models.DateTimeField(blank=True, null=True, verbose_name="上次成功同步时间")),
                ("last_error", models.TextField(blank=True, verbose_name="上次错误信息")),
            ],
            options={
                "verbose_name": "地理IP池同步状态",
                "verbose_name_plural": "地理IP池同步状态",
            },
        ),
    ]
