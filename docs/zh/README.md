# Django IP Safeguard

![版本](https://img.shields.io/badge/version-0.1.0-blue.svg)
![Django](https://img.shields.io/badge/Django-6.0-green.svg)
![Python](https://img.shields.io/badge/Python-3.10+-yellow.svg)
![许可证](https://img.shields.io/badge/License-MIT-orange.svg)

全面的 Django IP 风险管理插件，提供 IP 风险查询、地区规则和自动封禁功能。

## 功能特性

- **IP 风险评估**：查询多个威胁情报源的 IP 信誉
- **地理封禁**：基于国家/地区规则封禁或允许 IP
- **限流保护**：防止暴力破解和 DDoS 攻击
- **自动封禁系统**：基于可配置规则自动封禁恶意 IP
- **实时仪表盘**：监控访问日志、已封禁 IP 和安全事件
- **多因素认证**：支持 2FA 和 API 密钥认证
- **Celery 集成**：后台任务调度
- **Redis 缓存**：带熔断模式的高效缓存
- **国际化支持**：英语和中文

## 环境要求

- Python 3.10+
- Django 6.0+
- Redis 5.0+
- Node.js 18+（仅前端开发需要）

## 安装

### 从 PyPI 安装（推荐）

```bash
pip install django-ip-safeguard
```

### 从源码安装

```bash
git clone https://github.com/hayratjan/django_ip_safeguard.git
cd django_ip_safeguard
pip install -e .
```

### 开发环境安装

```bash
pip install -e ".[dev,geoip2]"
```

## 快速开始

### 1. 添加到 Django 设置

```python
# settings.py
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

ROOT_URLCONF = "your_project.urls"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
    }
}
```

### 2. 更新 URLs

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    # ...
    path("ip-guard/", include("django_ip_safeguard.urls")),
    # ...
]
```

### 3. 运行迁移

```bash
python manage.py migrate
```

### 4. 创建管理员用户

```bash
python manage.py createsuperuser
```

### 5. 构建前端（可选）

```bash
python manage.py build_frontend
```

### 6. 启动开发服务器

```bash
python manage.py runserver 8000
```

访问 `http://localhost:8000/ip-guard/` 进入管理仪表盘。

## 配置

### 基本设置

```python
# settings.py

IP_GUARD = {
    "ENABLED": True,
    "WHITELIST_IPS": ["127.0.0.1", "10.0.0.0/8"],
    "BLACKLIST_IPS": [],
    "DEFAULT_POLICY": "allow",
    "ENABLE_2FA": True,
    "JWT": {
        "SECRET_KEY": "your-secret-key-change-in-production",
        "ACCESS_TOKEN_LIFETIME_MINUTES": 60,
        "REFRESH_TOKEN_LIFETIME_DAYS": 7,
    },
    "CACHE": {
        "ENABLED": True,
        "BACKEND": "redis",
        "LOCATION": "redis://127.0.0.1:6379/1",
    },
    "RATE_LIMIT": {
        "ENABLED": True,
        "REQUESTS_PER_MINUTE": 60,
    },
    "AUTO_BAN": {
        "ENABLED": True,
        "THRESHOLD": 5,
        "DURATION_MINUTES": 30,
    },
}
```

完整配置项请参考 [docs/zh/04-configuration-reference.md](docs/zh/04-configuration-reference.md)

## 项目结构

```
django_ip_safeguard/
├── __init__.py           # 包初始化
├── admin.py              # Django admin 配置
├── apps.py               # 应用配置
├── celery.py             # Celery 配置
├── conf.py               # 设置管理
├── exceptions.py         # 自定义异常
├── middleware.py         # IP Guard 中间件
├── models.py             # 数据库模型
├── signals.py            # Django 信号
├── urls.py               # URL 路由
├── views.py              # API 视图
├── types.py              # 类型定义
├── services/             # 业务逻辑服务
│   ├── audit_service.py
│   ├── ban_service.py
│   ├── cache.py
│   ├── jwt_service.py
│   ├── policy_service.py
│   ├── risk_engine.py
│   └── ...
├── migrations/           # 数据库迁移
├── management/           # 自定义管理命令
│   └── commands/
├── locale/               # 翻译文件
└── contrib/
    └── admin_frontend/   # Vue.js 管理仪表盘
        ├── src/          # 前端源码
        ├── static/      # 构建的静态文件
        └── management/   # 前端构建命令
```

## 管理命令

```bash
# 构建前端资源
python manage.py build_frontend

# 同步 GeoIP 池
python manage.py sync_geo_ip_pools

# 更新 GeoIP 数据库
python manage.py update_geoip2_db

# 同步威胁情报
python manage.py sync_threat_intel

# 运行任务调度器
python manage.py run_task_scheduler

# 快照 IP 信誉
python manage.py snapshot_ip_reputation
```

## API 参考

### 认证

- `POST /ip-guard/api/auth/login/` - 用户登录
- `POST /ip-guard/api/auth/jwt/login/` - JWT 登录
- `POST /ip-guard/api/auth/jwt/refresh/` - 刷新 JWT
- `POST /ip-guard/api/auth/logout/` - 用户登出
- `GET /ip-guard/api/auth/me/` - 获取当前用户

### API 密钥

- `POST /ip-guard/api/auth/api-key/login/` - 使用 API 密钥登录
- `GET /ip-guard/api/auth/api-key/list/` - 列出 API 密钥
- `POST /ip-guard/api/auth/api-key/create/` - 创建 API 密钥
- `POST /ip-ground/api/auth/api-key/revoke/` - 撤销 API 密钥
- `GET /ip-guard/api/auth/api-key/logs/` - 获取 API 密钥使用日志

### 仪表盘

- `GET /ip-guard/api/dashboard/` - 仪表盘统计
- `GET /ip-guard/api/recent-records/` - 最近访问记录
- `GET /ip-guard/api/user-stats-chart/` - 用户统计图表

### 策略与访问控制

- `GET /ip-guard/api/policy/` - 获取当前策略
- `POST /ip-guard/api/ban/` - 封禁 IP
- `POST /ip-guard/api/unban/` - 解封 IP
- `GET /ip-guard/api/ban-list/` - 列出已封禁 IP
- `GET /ip-guard/api/access-logs/` - 访问日志

### 管理

- `GET /ip-guard/api/health/` - 健康检查
- `GET /ip-guard/api/system-settings/` - 系统设置
- `GET /ip-guard/api/security-audit-logs/` - 安全审计日志
- `GET /ip-guard/api/scheduled-tasks/` - 计划任务

## 前端仪表盘

包包含基于 Vue.js 的管理仪表盘：

- **仪表盘**：实时统计和图表
- **策略管理**：配置 IP 封禁规则
- **访问日志**：查看和搜索访问历史
- **封禁管理**：查看和管理已封禁 IP
- **用户设置**：API 密钥管理、2FA 设置
- **系统设置**：配置系统选项

访问 `/ip-guard/`

## 数据库模型

- `IpGuardPolicy`：主要策略配置
- `IpAccessLog`：访问日志记录
- `ApiKey`：API 密钥存储
- `ApiKeyUsageLog`：API 密钥使用日志
- `ScheduledTask`：计划任务定义
- `TaskExecutionLog`：任务执行历史
- `UserProfile`：支持 2FA 的扩展用户资料

## 开发

### 设置开发环境

```bash
# 克隆仓库
git clone https://github.com/hayratjan/django_ip_safeguard.git
cd django_ip_safeguard

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -e ".[dev,geoip2]"

# 运行测试
pytest

# 运行开发服务器
cd demo_project
python manage.py runserver
```

### 运行测试

```bash
pytest tests/ -v
```

## 文档

完整文档位于 `docs/` 目录：

- [快速开始](docs/zh/01-quick-start.md)
- [安装与环境要求](docs/zh/02-installation.md)
- [中间件与请求流程](docs/zh/03-middleware.md)
- [配置项完整参考](docs/zh/04-configuration-reference.md)
- [数据库模型](docs/zh/05-models.md)
- [API 参考](docs/zh/06-api-reference.md)
- [前端仪表盘](docs/zh/07-frontend-dashboard.md)
- [部署指南](docs/zh/08-deployment.md)
- [开发指南](docs/zh/09-development.md)

## 许可证

MIT 许可证 - 参见 [LICENSE](LICENSE) 文件。

## 贡献

欢迎贡献！请提交 Pull Request。
