# Quick Start Guide

This guide will help you get Django IP Safeguard up and running in 5 minutes.

## Prerequisites

- Python 3.10 or higher
- Django 6.0+
- Redis 5.0+ (optional but recommended)

## Installation

```bash
pip install django-ip-safeguard
```

## Django Settings

Add to your `settings.py`:

```python
INSTALLED_APPS = [
    # ...
    "django_ip_safeguard",
    "django.contrib.admin",
    # ...
]

MIDDLEWARE = [
    # ...
    "django_ip_safeguard.middleware.IpGuardMiddleware",
    # ...
]
```

## URL Configuration

Add to your `urls.py`:

```python
from django.urls import path, include

urlpatterns = [
    # ...
    path("ip-guard/", include("django_ip_safeguard.urls")),
    # ...
]
```

## Run Migrations

```bash
python manage.py migrate
```

## Create Admin User

```bash
python manage.py createsuperuser
```

## Start Server

```bash
python manage.py runserver 8000
```

Visit `http://localhost:8000/ip-guard/admin-frontend/` to access the admin dashboard.

## Next Steps

- [Configuration Reference](04-configuration-reference.md) - Customize IP Guard settings
- [API Reference](06-api-reference.md) - Use the REST API
- [Deployment Guide](08-deployment.md) - Deploy to production
