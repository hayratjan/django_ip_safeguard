# 快速开始

本指南将帮助您在 5 分钟内从 **PyPI** 安装并运行 Django IP Safeguard。

## 环境要求

- Python 3.10+
- Django 6.0+
- Redis 5.0+（情报缓存、封禁、限流、地理池等能力依赖 Redis，生产环境强烈建议启用）

## 从 PyPI 安装

- 包索引：<https://pypi.org/project/django-ip-safeguard/>
- 安装：`pip install django-ip-safeguard`
- 升级：`pip install -U django-ip-safeguard`
- 可选 GeoIP2：`pip install "django-ip-safeguard[geoip2]"`

## Django 设置

在 `settings.py` 中注册应用；**中间件顺序**建议：`SecurityMiddleware` → `SessionMiddleware` → **`IpGuardMiddleware`** → `CommonMiddleware` → `CsrfViewMiddleware` → `AuthenticationMiddleware` → …（IP 判定尽量靠前，且晚于 Session 以便会话 Cookie 正常）。

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

生产环境若控制台与 API 不在同源，请配置 `CSRF_TRUSTED_ORIGINS`。可选使用 **`IP_GUARD` 嵌套字典** 管理配置，说明见 [安装与环境要求](02-installation.md)。

## URL 配置

在根 `urls.py` 挂载（内置 Vue 构建产物，前缀为 `/ip-guard/`）：

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

浏览器访问 **`http://127.0.0.1:8000/ip-guard/`** 进入管理控制台（需已登录且有相应模型权限）。

## 下一步

- [配置参考](04-configuration-reference.md) - 自定义 IP Guard 设置
- [API 参考](06-api-reference.md) - 使用 REST API
- [部署指南](08-deployment.md) - 部署到生产环境
