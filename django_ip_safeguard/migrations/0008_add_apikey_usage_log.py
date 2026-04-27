# ApiKeyUsageLog 已在 0007_add_2fa_lock_fields 中创建；本迁移保留编号避免已部署环境混乱，无新操作。

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("django_ip_safeguard", "0007_add_2fa_lock_fields"),
    ]

    operations = []
