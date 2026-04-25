from django.apps import AppConfig


class DjangoIpSafeguardConfig(AppConfig):
    """Django 应用配置。"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "django_ip_safeguard"
    verbose_name = "Django IP Safeguard"
