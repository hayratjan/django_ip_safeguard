# Installation & Requirements

## System Requirements

### Python

- Python 3.10, 3.11, 3.12, 3.13, or 3.14
- Django 6.0+

### Databases

- SQLite 3.33+ (development)
- PostgreSQL 12+ (production)
- MySQL 8.0+ (production)

### External Services

- Redis 5.0+ (optional but recommended for caching)

## Installation Methods

### From PyPI

```bash
pip install django-ip-safeguard
```

### From Source

```bash
git clone https://github.com/hayratjan/django_ip_safeguard.git
cd django_ip_safeguard
pip install -e .
```

### With GeoIP2 Support

```bash
pip install django-ip-safeguard[geoip2]
```

### Development Installation

```bash
pip install -e ".[dev,geoip2]"
```

## Dependencies

### Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| Django | >=6.0 | Web framework |
| redis | >=5.0.0 | Caching backend |
| httpx | >=0.27.0 | HTTP client for threat intel |
| PyJWT | >=2.8.0 | JWT authentication |
| django-unfold | >=0.40.0 | Admin theme |
| pyotp | >=2.9.0 | TOTP for 2FA |
| qrcode | >=7.4 | QR code generation |
| celery | >=5.3.0 | Async task queue |
| django-celery-beat | >=2.5.0 | Celery scheduler |
| croniter | >=2.0.0 | Cron parsing |

### Optional Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| geoip2 | >=4.0.0 | GeoIP database lookup |

## Environment Setup

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows
```

### 2. Install Django IP Safeguard

```bash
pip install django-ip-safeguard
```

### 3. Configure Django Project

Create a new Django project or use an existing one:

```bash
django-admin startproject myproject
cd myproject
```

### 4. Add to Django Settings

Edit `myproject/settings.py`:

```python
INSTALLED_APPS = [
    # ...
    "django_ip_safeguard",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    # ...
]

MIDDLEWARE = [
    # ...
    "django_ip_safeguard.middleware.IpGuardMiddleware",
    # ...
]
```

### 5. Configure URLs

Edit `myproject/urls.py`:

```python
from django.urls import path, include

urlpatterns = [
    # ...
    path("ip-guard/", include("django_ip_safeguard.urls")),
    # ...
]
```

### 6. Run Migrations

```bash
python manage.py migrate
```

### 7. Create Superuser

```bash
python manage.py createsuperuser
```

### 8. Build Frontend

```bash
python manage.py build_frontend
```

### 9. Run Development Server

```bash
python manage.py runserver 8000
```

Visit `http://localhost:8000/ip-guard/admin-frontend/`

## Production Setup

### Using with PostgreSQL

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "ip_guard_db",
        "USER": "postgres",
        "PASSWORD": "your-password",
        "HOST": "localhost",
        "PORT": "5432",
    }
}
```

### Using with Redis

```python
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
    }
}
```

### Using with Celery

```python
# settings.py
CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
```

### Using Supervisor for Celery

```ini
[program:celery]
command=cd /path/to/project && celery -A your_project worker -l info
directory=/path/to/project
user=www-data
autostart=true
autorestart=true
stdout_logfile=/var/log/celery.log
stderr_logfile=/var/log/celery_error.log
```

## Next Steps

- [Configuration Reference](04-configuration-reference.md) - Configure IP Guard settings
- [Middleware Flow](03-middleware.md) - Understand request processing
