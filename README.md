# django-ip-safeguard

Django IP 风险拦截插件，支持 IP 风险查询、地区规则控制和自动封禁。

## 快速开始

1. 安装：

```bash
pip install django-ip-safeguard
```

2. 在 `INSTALLED_APPS` 中加入：

```python
INSTALLED_APPS = [
    # ...
    "django_ip_safeguard",
]
```

3. 在 `MIDDLEWARE` 前置加入：

```python
MIDDLEWARE = [
    "django_ip_safeguard.middleware.IpGuardMiddleware",
    # ...
]
```

4. 配置示例：

```python
IP_GUARD_ENABLED = True
IP_GUARD_REDIS_URL = "redis://127.0.0.1:6379/0"
IP_GUARD_PROVIDER = "http"  # dummy/http
IP_GUARD_PROVIDER_ENDPOINT = "https://your-ip-intel-api.example.com/query"
IP_GUARD_PROVIDER_API_KEY = "your-api-key"
IP_GUARD_PROVIDER_TIMEOUT = 3.0
IP_GUARD_PROVIDER_MAX_RETRIES = 2
IP_GUARD_PROVIDER_RETRY_BACKOFF = 0.2
IP_GUARD_PROVIDER_HEADERS = {"X-Source": "django-ip-safeguard"}
IP_GUARD_RISK_SCORE_THRESHOLD = 70
IP_GUARD_ALLOWED_COUNTRIES = ("CN", "SG")
IP_GUARD_FAIL_OPEN = True
IP_GUARD_FAIL_OPEN_PATH_PREFIXES = ("/public",)
IP_GUARD_FAIL_CLOSE_PATH_PREFIXES = ("/api/login", "/api/pay")
IP_GUARD_TRUSTED_PROXY_CIDRS = ("127.0.0.1/32",)
IP_GUARD_USE_DB_LOG = False
```

## 开发命令

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
ruff check .
```
