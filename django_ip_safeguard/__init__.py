default_app_config = "django_ip_safeguard.apps.DjangoIpSafeguardConfig"

__all__ = ["default_app_config"]

try:
    from django_ip_safeguard.celery import app as celery_app
except ImportError:
    celery_app = None
