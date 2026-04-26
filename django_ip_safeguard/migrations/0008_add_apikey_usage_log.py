from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('django_ip_safeguard', '0007_add_2fa_lock_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='ApiKeyUsageLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP地址')),
                ('user_agent', models.TextField(blank=True, default='', verbose_name='User Agent')),
                ('action', models.CharField(default='login', max_length=32, verbose_name='操作')),
                ('success', models.BooleanField(default=True, verbose_name='是否成功')),
                ('failure_reason', models.CharField(blank=True, default='', max_length=128, verbose_name='失败原因')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('api_key', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='usage_logs', to='django_ip_safeguard.apikey', verbose_name='API密钥')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='api_key_usage_logs', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
            ],
            options={
                'verbose_name': 'API密钥使用日志',
                'verbose_name_plural': 'API密钥使用日志',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='apikeyusagelog',
            index=models.Index(fields=['-created_at'], name='apikey_usag_created_idx'),
        ),
        migrations.AddIndex(
            model_name='apikeyusagelog',
            index=models.Index(fields=['api_key', '-created_at'], name='apikey_usag_api_key_idx'),
        ),
    ]
