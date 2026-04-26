from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class DjangoIpSafeguardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_ip_safeguard"
    verbose_name = _("IP安全卫士")

    def ready(self):
        import django_ip_safeguard.signals  # noqa: F401
