# django-ip-safeguard Enterprise

<div align="center">
  <img src="assets/logo.svg" alt="django-ip-safeguard logo" width="180" />
</div>

<p align="center">
  企业级 Django IP 风险防护中间件与运营控制台
</p>

<p align="center">
  <img src="https://img.shields.io/badge/enterprise-ready-0F766E.svg" alt="enterprise-ready" />
  <img src="https://img.shields.io/badge/security-hardened-166534.svg" alt="security-hardened" />
  <img src="https://img.shields.io/badge/django-4.2%2B-0C4B33.svg" alt="django" />
  <img src="https://img.shields.io/badge/python-3.9%2B-3776AB.svg" alt="python" />
</p>

## 📌 项目简介

`django-ip-safeguard` 是一个面向企业生产环境的 Django 请求前置安全插件。  
它在请求进入业务视图前完成 IP 风险识别、地区策略校验、缓存决策复用和封禁治理，并提供企业 Dashboard 与策略中心。

## 🧭 企业能力总览

- `🛡️ 请求前置防护`：中间件早期阻断风险流量，减少业务层压力。
- `🌍 风险与地区策略`：支持风险分阈值、风险标签、国家白黑名单。
- `⚙️ 策略中心`：支持数据库策略覆盖 `settings`（策略即时生效）。
- `📊 Dashboard`：提供统计面板、策略接口、健康检查、解封接口。
- `🔐 安全加固`：管理接口权限控制、API Key 环境变量化、IP 脱敏审计。
- `🚀 高可用`：熔断、重试、并发去重锁、分级缓存 TTL、降级策略。

## 🏗️ 企业架构说明

1. 请求进入 `IpGuardMiddleware`。
2. 读取运行时策略（数据库策略优先，其次 `settings`）。
3. 先查封禁缓存，再查情报缓存。
4. 缓存未命中时调用 Provider，并应用并发去重和熔断策略。
5. 风险引擎判定放行/阻断。
6. 记录审计日志（可配置脱敏）。
7. Dashboard 对外提供管理与运营数据接口。

## ⚡ 快速接入（企业版）

### 1) 安装

```bash
pip install django-ip-safeguard
```

### 2) 注册 App 与中间件

```python
INSTALLED_APPS = [
    # ...
    "django_ip_safeguard",
]

MIDDLEWARE = [
    "django_ip_safeguard.middleware.IpGuardMiddleware",
    # ...
]
```

### 3) 挂载企业控制台 URL

```python
from django.urls import include, path

urlpatterns = [
    path("ip-guard/", include("django_ip_safeguard.urls")),
]
```

### 4) 执行迁移

```bash
python manage.py migrate
```

### 5) 设置最小生产配置

```python
import os

IP_GUARD_ENABLED = True
IP_GUARD_REDIS_URL = "redis://127.0.0.1:6379/0"
IP_GUARD_PROVIDER = "http"
IP_GUARD_PROVIDER_ENDPOINT = "https://risk-api.example.com/ip/query"
IP_GUARD_PROVIDER_API_KEY = os.getenv("IP_GUARD_PROVIDER_API_KEY", "")
IP_GUARD_RISK_SCORE_THRESHOLD = 70
IP_GUARD_TRUSTED_PROXY_CIDRS = ("10.0.0.0/8",)
```

## 🧩 配置分组说明

### `🔧 基础开关`

- `IP_GUARD_ENABLED`
- `IP_GUARD_REDIS_URL`
- `IP_GUARD_CACHE_TTL`
- `IP_GUARD_BAN_TTL`
- `IP_GUARD_BLOCK_STATUS_CODE`
- `IP_GUARD_USE_DB_LOG`
- `IP_GUARD_ENABLE_POLICY_CENTER`
- `IP_GUARD_POLICY_CACHE_SECONDS`

### `🌐 Provider`

- `IP_GUARD_PROVIDER`
- `IP_GUARD_PROVIDER_ENDPOINT`
- `IP_GUARD_PROVIDER_API_KEY`（建议仅环境变量）
- `IP_GUARD_PROVIDER_TIMEOUT`
- `IP_GUARD_PROVIDER_MAX_RETRIES`
- `IP_GUARD_PROVIDER_RETRY_BACKOFF`
- `IP_GUARD_PROVIDER_CIRCUIT_BREAKER_FAILURES`
- `IP_GUARD_PROVIDER_CIRCUIT_BREAKER_TTL`
- `IP_GUARD_PROVIDER_HEADERS`

### `🛡️ 风险规则`

- `IP_GUARD_RISK_SCORE_THRESHOLD`
- `IP_GUARD_BLOCKED_RISK_TAGS`
- `IP_GUARD_ALLOWED_COUNTRIES`
- `IP_GUARD_BLOCKED_COUNTRIES`
- `IP_GUARD_IP_WHITELIST`（单 IP 或 CIDR；命中直接放行）
- `IP_GUARD_IP_BLACKLIST`（单 IP 或 CIDR；启用策略中心时以数据库策略为准）
- `IP_GUARD_RATE_LIMIT_PER_MINUTE`（单 IP 每分钟请求上限，`0` 关闭；需 Redis）

### `🧯 降级与高可用`

- `IP_GUARD_FAIL_OPEN`
- `IP_GUARD_FAIL_OPEN_PATH_PREFIXES`
- `IP_GUARD_FAIL_CLOSE_PATH_PREFIXES`
- `IP_GUARD_DEDUPE_LOCK_SECONDS`
- `IP_GUARD_HIGH_RISK_CACHE_TTL`
- `IP_GUARD_LOW_RISK_CACHE_TTL`

### `🔐 审计与合规`

- `IP_GUARD_IP_MASK_ENABLED`
- `IP_GUARD_IP_MASK_KEEP_PREFIX`

## 📊 Dashboard 与管理接口

- `GET /ip-guard/`：企业管理面板入口
- `GET /ip-guard/api/dashboard/`：24h 统计、拦截率、决策分布、按小时趋势、Top 风险 IP、国家/路径/拦截原因分布
- `GET /ip-guard/api/recent-records/`：近 `days` 天（1–30）访问/拦截按日汇总、最新拦截与访问记录、近期封禁（需开启审计写库才有数据）
- `GET /ip-guard/api/policy/`：读取当前策略
- `POST /ip-guard/api/policy/`：更新策略（支持 IP/CIDR 白黑名单与地区白黑名单；自动校验与去重）
- `POST /ip-guard/api/ban/`、`POST /ip-guard/api/unban/`、`GET /ip-guard/api/ban-list/`：封禁管理与分页列表
- `GET /ip-guard/api/access-logs/`：审计分页（路径、日期等筛选）
- `GET /ip-guard/api/access-logs/export/`：审计 CSV 导出（与列表相同筛选，上限 1 万条）
- `GET /ip-guard/api/health/`：Redis 连通与延迟、Provider、熔断失败计数、策略中心开关
- JWT 配置：`IP_GUARD_JWT_SECRET_KEY`、`IP_GUARD_JWT_ALGORITHM`、`IP_GUARD_JWT_ACCESS_TTL`、`IP_GUARD_JWT_REFRESH_TTL`

## ✅ 企业上线检查清单

- 已开启受信代理网段，避免伪造 `X-Forwarded-For`。
- API Key 通过环境变量注入，不落盘。
- 关键路径已设置 `fail-close`（登录/支付/管理端）。
- 已配置白名单（办公网、探针、健康检查）。
- 已开启审计日志与 IP 脱敏。
- 已验证熔断、降级、Redis 异常场景行为。
- 已跑通 `pytest` 与 `ruff`。

## 🧪 开发与验证命令

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
ruff check .
```

## 📚 文档导航

- 企业完整指南：`docs/django-ip-guard-开发与发布指南.md`
- 企业发布流程：`docs/django-ip-guard-开发与发布指南.md` 中 “PyPI 发布流程”

## 🖥️ Vue3 企业控制台（Element Plus）

新增目录：`frontend-admin/`，技术栈为 Vue3 + Vite + Element Plus + Pinia + Axios。

### 本地启动

```bash
cd frontend-admin
npm install
npm run dev
```

默认地址：`http://127.0.0.1:5173`

### 后端联调要求

- Django 服务运行在 `http://127.0.0.1:8010`
- 前端通过 Vite 代理访问 `/ip-guard/api/*`
- 鉴权采用 Django Session + CSRF：
  1. `GET /ip-guard/api/auth/csrf/`
  2. `POST /ip-guard/api/auth/login/`
  3. `GET /ip-guard/api/auth/me/`（返回 `groups` 与 `permissions`）
- 所有管理 API 视图均显式启用 `csrf_protect`，写操作必须携带有效 `X-CSRFToken`。
- 控制台基于 Django 用户与组权限显示菜单并限制访问：
  - `django_ip_safeguard.view_ipaccesslog`：仪表盘/审计日志/近期记录
  - `django_ip_safeguard.view_ipguardpolicy`：策略中心查看、健康状态
  - `django_ip_safeguard.change_ipguardpolicy`：策略中心修改
  - `django_ip_safeguard.view_ipbanrecord`：封禁列表查看
  - `django_ip_safeguard.change_ipbanrecord`：手动封禁/解封

### 已实现页面

- 登录页：`/login`
- 仪表盘：`/dashboard`（含 ECharts 国际来源世界地图 + 国家 Top 条形图）
- 策略中心：`/policy`
- 封禁管理：`/ban`
- 审计日志：`/logs`
- 健康状态：`/health`
