# 快速开始

本指南将帮助您在 5 分钟内启动并运行 Django IP Safeguard。

## 环境要求

- Python 3.10 或更高
- Django 6.0+
- Redis 5.0+（可选但推荐）

## 安装

```bash
pip install django-ip-safeguard
```

## Django 设置

添加到 `settings.py`：

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

## URL 配置

添加到 `urls.py`：

```python
from django.urls import path, include

urlpatterns = [
    # ...
    path("ip-guard/", include("django_ip_safeguard.urls")),
    # ...
]
```

## 运行迁移

```bash
python manage.py migrate
```

## 创建管理员用户

```bash
python manage.py createsuperuser
```

## 启动服务器

```bash
python manage.py runserver 8000
```

访问 `http://localhost:8000/ip-guard/` 进入管理仪表盘。

## 下一步

- [配置参考](04-configuration-reference.md) - 自定义 IP Guard 设置
- [API 参考](06-api-reference.md) - 使用 REST API
- [部署指南](08-deployment.md) - 部署到生产环境
