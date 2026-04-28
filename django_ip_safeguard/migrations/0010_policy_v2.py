# 0010 策略引擎 v2：多策略路由 + 加权打分 + 分级动作 + 变更快照

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("django_ip_safeguard", "0009_scheduled_task"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="ipguardpolicy",
            name="priority",
            field=models.IntegerField(
                default=10000,
                help_text="数值越小越优先匹配；default 策略请保持较大值作为兜底",
                verbose_name="匹配优先级",
            ),
        ),
        migrations.AddField(
            model_name="ipguardpolicy",
            name="match_host_regex",
            field=models.CharField(
                blank=True,
                default="",
                help_text="空表示不限制；匹配 request.get_host() 去掉端口后的主机名",
                max_length=256,
                verbose_name="Host 正则",
            ),
        ),
        migrations.AddField(
            model_name="ipguardpolicy",
            name="match_path_prefixes",
            field=models.JSONField(blank=True, default=list, verbose_name="路径前缀列表"),
        ),
        migrations.AddField(
            model_name="ipguardpolicy",
            name="match_methods",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='空表示任意方法；如 ["GET","POST"]',
                verbose_name="HTTP 方法列表",
            ),
        ),
        migrations.AddField(
            model_name="ipguardpolicy",
            name="tier_thresholds",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='示例 {"medium": 40, "high": 70}；high 缺省时用风险阈值 risk_score_threshold',
                verbose_name="分级阈值",
            ),
        ),
        migrations.AddField(
            model_name="ipguardpolicy",
            name="signal_weights",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='如 {"risk_score":1.0,"tag_blocked":50}；空则使用内置默认',
                verbose_name="信号权重",
            ),
        ),
        migrations.AddField(
            model_name="ipguardpolicy",
            name="medium_action",
            field=models.CharField(
                choices=[
                    ("allow", "放行"),
                    ("log_only", "仅记录"),
                    ("rate_limit", "限流"),
                    ("challenge", "挑战/二次校验"),
                    ("block", "拦截"),
                    ("ban", "拦截并封禁"),
                ],
                default="block",
                max_length=32,
                verbose_name="中风险动作",
            ),
        ),
        migrations.AddField(
            model_name="ipguardpolicy",
            name="high_action",
            field=models.CharField(
                choices=[
                    ("allow", "放行"),
                    ("log_only", "仅记录"),
                    ("rate_limit", "限流"),
                    ("challenge", "挑战/二次校验"),
                    ("block", "拦截"),
                    ("ban", "拦截并封禁"),
                ],
                default="ban",
                max_length=32,
                verbose_name="高风险动作",
            ),
        ),
        migrations.AlterModelOptions(
            name="ipguardpolicy",
            options={
                "ordering": ["priority", "name"],
                "verbose_name": "IP防护策略",
                "verbose_name_plural": "IP防护策略",
            },
        ),
        migrations.CreateModel(
            name="IpGuardPolicySnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("before_json", models.JSONField(blank=True, default=dict, verbose_name="变更前")),
                ("after_json", models.JSONField(blank=True, default=dict, verbose_name="变更后")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ip_guard_policy_snapshots",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="操作人",
                    ),
                ),
                (
                    "policy",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="snapshots",
                        to="django_ip_safeguard.ipguardpolicy",
                        verbose_name="策略",
                    ),
                ),
            ],
            options={
                "verbose_name": "IP策略变更快照",
                "verbose_name_plural": "IP策略变更快照",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="ipguardpolicysnapshot",
            index=models.Index(fields=["policy", "-created_at"], name="ipg_pol_snap_idx"),
        ),
    ]
