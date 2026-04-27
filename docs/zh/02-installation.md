# 安装与环境要求

## 系统要求

### Python

- Python 3.10, 3.11, 3.12, 3.13, 或 3.14
- Django 6.0+

### 数据库

- SQLite 3.33+（开发）
- PostgreSQL 12+（生产）
- MySQL 8.0+（生产）

### 外部服务

- Redis 5.0+（可选但推荐）

## 安装方式

### 从 PyPI 安装

```bash
pip install django-ip-safeguard
```

### 从源码安装

```bash
git clone https://github.com/hayratjan/django_ip_safeguard.git
cd django_ip_safeguard
pip install -e .
```

### 带 GeoIP2 支持

```bash
pip install django-ip-safeguard[geoip2]
```

### 开发环境安装

```bash
pip install -e ".[dev,geoip2]"
```

## 依赖

### 核心依赖

| 包 | 版本 | 用途 |
|----|------|------|
| Django | >=6.0 | Web 框架 |
| redis | >=5.0.0 | 缓存后端 |
| httpx | >=0.27.0 | 威胁情报 HTTP 客户端 |
| PyJWT | >=2.8.0 | JWT 认证 |
| django-unfold | >=0.40.0 | Admin 主题 |
| pyotp | >=2.9.0 | TOTP 2FA |
| qrcode | >=7.4 | 二维码生成 |
| celery | >=5.3.0 | 异步任务队列 |
| django-celery-beat | >=2.5.0 | Celery 调度器 |
| croniter | >=2.0.0 | Cron 解析 |

### 可选依赖

| 包 | 版本 | 用途 |
|----|------|------|
| geoip2 | >=4.0.0 | GeoIP 数据库查询 |

## 环境配置

### 1. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate  # Windows
```

### 2. 安装 Django IP Safeguard

```bash
pip install django-ip-safeguard
```

### 3. 配置 Django 项目

```bash
django-admin startproject myproject
cd myproject
```

### 4. 添加到 Django 设置

编辑 `myproject/settings.py`：

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

### 5. 配置 URLs

编辑 `myproject/urls.py`：

```python
from django.urls import path, include

urlpatterns = [
    # ...
    path("ip-guard/", include("django_ip_safeguard.urls")),
    # ...
]
```

### 6. 运行迁移

```bash
python manage.py migrate
```

### 7. 创建超级用户

```bash
python manage.py createsuperuser
```

### 8. 构建前端

```bash
python manage.py build_frontend
```

### 9. 启动开发服务器

```bash
python manage.py runserver 8000
```

访问 `http://localhost:8000/ip-guard/admin-frontend/`

## 生产环境配置

### 使用 PostgreSQL

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

### 使用 Redis

```python
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
    }
}
```

### 使用 Celery

```python
# settings.py
CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
```

## 下一步

- [配置参考](04-configuration-reference.md) - 配置 IP Guard 设置
- [中间件流程](03-middleware.md) - 理解请求处理
