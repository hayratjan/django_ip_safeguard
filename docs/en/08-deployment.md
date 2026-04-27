# Deployment Guide

## Production Requirements

- Python 3.10+
- Django 6.0+
- PostgreSQL 12+ (recommended) or MySQL 8.0+
- Redis 5.0+
- Nginx or Apache
- Gunicorn or uWSGI

## Checklist

Before deploying to production:

1. Set `DEBUG=False`
2. Configure `ALLOWED_HOSTS`
3. Use strong `SECRET_KEY`
4. Use HTTPS
5. Configure Redis caching
6. Set up proper logging
7. Run migrations
8. Build frontend

## Configuration

### Environment Variables

```bash
# Django settings
export DJANGO_SECRET_KEY='your-production-secret-key'
export DJANGO_DEBUG=False
export DJANGO_ALLOWED_HOSTS='example.com,www.example.com'

# Database
export DATABASE_URL='postgres://user:pass@localhost:5432/ipguard'

# Redis
export REDIS_URL='redis://localhost:6379/1'
```

### Production Settings

```python
# settings.py
import os

DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'True'

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'ipguard',
        'USER': 'postgres',
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Redis Cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://localhost:6379/1'),
    }
}

# Security
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django_ip_safeguard.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'WARNING',
        },
    },
}
```

## Gunicorn Setup

```bash
pip install gunicorn
```

Create `gunicorn_config.py`:

```python
bind = "127.0.0.1:8000"
workers = 4
worker_class = "sync"
max_requests = 1000
timeout = 30
accesslog = "/var/log/gunicorn_access.log"
errorlog = "/var/log/gunicorn_error.log"
```

Run:

```bash
gunicorn -c gunicorn_config.py your_project.wsgi:application
```

## Nginx Configuration

```nginx
upstream ip_guard {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    client_max_body_size 10M;

    location / {
        proxy_pass http://ip_guard;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/admin_frontend/ {
        alias /path/to/django_ip_safeguard/contrib/admin_frontend/static/admin_frontend/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

## Celery Setup

```bash
pip install celery[redis]
```

Create `celery.py`:

```python
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')

app = Celery('your_project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
)
```

Supervisor config:

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

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py migrate
RUN python manage.py build_frontend

EXPOSE 8000

CMD ["gunicorn", "-c", "gunicorn_config.py", "your_project.wsgi:application"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
    environment:
      - DATABASE_URL=postgres://postgres:postgres@db:5432/ipguard
      - REDIS_URL=redis://redis:6379/1

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: ipguard
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    volumes:
      - redis_data:/data

  celery:
    build: .
    command: celery -A your_project worker -l info
    depends_on:
      - db
      - redis

volumes:
  postgres_data:
  redis_data:
```

## Deployment Steps

1. Clone repository
2. Install dependencies: `pip install -e .`
3. Configure environment variables
4. Run migrations: `python manage.py migrate`
5. Build frontend: `python manage.py build_frontend`
6. Collect static files: `python manage.py collectstatic`
7. Start services (Gunicorn, Celery, Nginx)

## Monitoring

### Health Check Endpoint

```bash
curl http://localhost:8000/ip-guard/api/health/
```

### Celery Worker Status

```bash
celery -A your_project inspect active
celery -A your_project inspect stats
```

## Backup

Regular backups for:
- Database (PostgreSQL/MySQL)
- Redis data
- Configuration files
- Uploaded files
