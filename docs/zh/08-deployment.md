# 部署指南

## 生产环境要求

- Python 3.10+
- Django 6.0+
- PostgreSQL 12+（推荐）或 MySQL 8.0+
- Redis 5.0+
- Nginx 或 Apache
- Gunicorn 或 uWSGI

## 检查清单

部署到生产环境之前：

1. 设置 `DEBUG=False`
2. 配置 `ALLOWED_HOSTS`
3. 使用强密码 `SECRET_KEY`
4. 使用 HTTPS
5. 配置 Redis 缓存
6. 设置适当的日志记录
7. 运行迁移
8. 构建前端

## 配置

### 环境变量

```bash
# Django 设置
export DJANGO_SECRET_KEY='your-production-secret-key'
export DJANGO_DEBUG=False
export DJANGO_ALLOWED_HOSTS='example.com,www.example.com'

# 数据库
export DATABASE_URL='postgres://user:pass@localhost:5432/ipguard'

# Redis
export REDIS_URL='redis://localhost:6379/1'
```

### 生产设置

```python
# settings.py
import os

DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'True'

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')

# 数据库
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

# Redis 缓存
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://localhost:6379/1'),
    }
}

# 安全
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# 日志
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

## Gunicorn 配置

```bash
pip install gunicorn
```

创建 `gunicorn_config.py`：

```python
bind = "127.0.0.1:8000"
workers = 4
worker_class = "sync"
max_requests = 1000
timeout = 30
accesslog = "/var/log/gunicorn_access.log"
errorlog = "/var/log/gunicorn_error.log"
```

运行：

```bash
gunicorn -c gunicorn_config.py your_project.wsgi:application
```

## Nginx 配置

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

## Celery 配置

```bash
pip install celery[redis]
```

创建 `celery.py`：

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

Supervisor 配置：

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

## Docker 部署

### 根目录 `requirements.txt`（如何维护）

- **事实来源**：运行时依赖以仓库根目录 [pyproject.toml](../../pyproject.toml) 中 `[project] dependencies` 为准；根目录 `requirements.txt` 为锁定版本后的派生文件，用于 Docker 等可复现安装，**不要与 `pyproject.toml` 手写双份维护**。
- **更新流程**：先修改 `pyproject.toml`，再在仓库根执行其一即可重新生成：
  - 推荐（与当前仓库生成方式一致，解析目标为 Python 3.12）：`uv pip compile pyproject.toml -o requirements.txt --python 3.12`
  - 或在使用 **pip-tools** 且 Python **≥3.10** 的环境中：`pip-compile pyproject.toml -o requirements.txt`
- **可选 GeoIP2**：若需把 `[project.optional-dependencies]` 中的 `geoip2` 打进同一份文件，可使用 `uv pip compile pyproject.toml -o requirements.txt --python 3.12 --extra geoip2`，或 `pip-compile pyproject.toml --extra geoip2 -o requirements.txt`。

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

## 部署步骤

1. 克隆仓库
2. 安装依赖：`pip install -e .`
3. 配置环境变量
4. 运行迁移：`python manage.py migrate`
5. 构建前端：`python manage.py build_frontend`
6. 收集静态文件：`python manage.py collectstatic`
7. 启动服务（Gunicorn、Celery、Nginx）

## 监控

### 健康检查端点

```bash
curl http://localhost:8000/ip-guard/api/health/
```

### Celery Worker 状态

```bash
celery -A your_project inspect active
celery -A your_project inspect stats
```

## 备份

定期备份：
- 数据库（PostgreSQL/MySQL）
- Redis 数据
- 配置文件
- 上传的文件
