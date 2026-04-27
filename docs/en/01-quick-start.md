# Quick Start Guide

This guide helps you install from **PyPI** and run Django IP Safeguard in about 5 minutes.

## Prerequisites

- Python 3.10+
- Django 6.0+
- Redis 5.0+ (recommended for production: intel cache, bans, rate limits, geo pools)

## Install from PyPI

- Package page: <https://pypi.org/project/django-ip-safeguard/>
- Install: `pip install django-ip-safeguard`
- Upgrade: `pip install -U django-ip-safeguard`
- Optional GeoIP2: `pip install "django-ip-safeguard[geoip2]"`

## Django Settings

Register the app in `settings.py`. **Middleware order** (recommended): `SecurityMiddleware` → `SessionMiddleware` → **`IpGuardMiddleware`** → `CommonMiddleware` → `CsrfViewMiddleware` → `AuthenticationMiddleware` → …

```python
INSTALLED_APPS = [
    # ...
    "django_ip_safeguard",
    "django.contrib.admin",
    # ...
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django_ip_safeguard.middleware.IpGuardMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # ...
]
```

For cross-origin deployments, set `CSRF_TRUSTED_ORIGINS`. You may group settings in a nested **`IP_GUARD`** dict; see [Installation](02-installation.md).

## URL Configuration

Mount the built-in dashboard and APIs under `/ip-guard/`:

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

Open **`http://127.0.0.1:8000/ip-guard/`** (sign in; permissions apply per model).

## Next Steps

- [Configuration Reference](04-configuration-reference.md) - Customize IP Guard settings
- [API Reference](06-api-reference.md) - Use the REST API
- [Deployment Guide](08-deployment.md) - Deploy to production
