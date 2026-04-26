import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demo_site.settings")

app = Celery("django_ip_safeguard")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
