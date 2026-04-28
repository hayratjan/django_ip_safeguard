import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demo_site.settings")
django.setup()
