# 中间件与请求流程

## 概述

`IpGuardMiddleware` 是 Django IP Safeguard 的核心组件。它拦截所有传入的 HTTP 请求并根据配置的安全策略进行评估。

## 请求处理流程（v0.2.0）

```
传入请求
    │
    ▼
┌──────────────────────────────┐
│ skip_path_prefixes (健康检查) │── 命中：直接放行
└──────────────────────────────┘
    │
    ▼
┌──────────────────────────────┐
│ load_effective_policy        │
│ 多策略路由：按 host/path/method│
│ 选 priority 最小的命中策略     │
└──────────────────────────────┘
    │
    ▼
┌──────────────────────────────┐
│ 白名单 → 黑名单 → 地理池      │
│ → 限流 → 已封禁缓存            │
└──────────────────────────────┘
    │ 任一命中：build_response(action)
    ▼
┌──────────────────────────────┐
│ 情报缓存命中？               │── 是 → 风险引擎评估
└──────────────────────────────┘
    │ 否
    ▼
┌──────────────────────────────┐
│ acquire_intel_lock           │
│  失败 → 短暂等待 + 重读缓存    │
│  仍无 → fail-open / fail-close │
└──────────────────────────────┘
    │ 取得锁
    ▼
┌──────────────────────────────┐
│ 调用情报 Provider            │
│  失败：熔断 + fail-open 判断   │
│  成功：set_intel + 释放锁     │
└──────────────────────────────┘
    │
    ▼
┌──────────────────────────────┐
│ 风险引擎 v2：加权分 + 分级      │
│ score < medium → allow         │
│ medium..high   → medium_action │
│ ≥ high         → high_action   │
└──────────────────────────────┘
    │
    ▼
   action_executor.build_response（按 Accept 返回 JSON / HTML）
    │
    ▼
   log_access_decision（统一审计）
```

> 任一拦截分支都会写访问日志，封禁分支也会一并写入，便于审计排错。

## 中间件配置

### 基本配置

```python
# settings.py
IP_GUARD = {
    "ENABLED": True,
    "WHITELIST_IPS": ["127.0.0.1", "10.0.0.0/8"],
    "BLACKLIST_IPS": ["192.168.1.100"],
    "DEFAULT_POLICY": "allow",
}
```

### 中间件顺序

中间件应放置在中间件堆栈的早期位置，以便在实际访问视图之前拦截请求：

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django_ip_safeguard.middleware.IpGuardMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # ... 其他中间件
]
```

## IP 地址检测

中间件自动检测客户端 IP 地址，考虑：

1. `X-Forwarded-For` 头（代理请求）
2. `X-Real-IP` 头
3. `REMOTE_ADDR` 服务器变量

### 信任的代理

```python
IP_GUARD = {
    "TRUSTED_PROXIES": ["10.0.0.0/8", "172.16.0.0/12"],
}
```

## 策略评估

### 策略优先级

1. 白名单 IP（始终允许）
2. 黑名单 IP（始终阻止）
3. 限流规则
4. 风险评估结果
5. GeoIP 规则
6. 默认策略

### 策略动作（v0.2.0 已落地）

| 动作 | HTTP 状态 | 是否封禁 | 描述 |
|------|----------|----------|------|
| `allow` | 200 | 否 | 放行 |
| `log_only` | 200 | 否 | 仅记录访问日志，行为同放行（用于灰度） |
| `rate_limit` | 429 | 否 | 限速类响应（与 rate_limit_per_minute 一致） |
| `challenge` | `challenge_status_code`（默认 403） | 否 | 自定义状态码用于二次校验/CAPTCHA |
| `block` | `block_status_code`（默认 403） | 否 | 拦截 |
| `ban` | `block_status_code` | 是（写入 Redis ban，TTL=`ban_ttl`） | 拦截并封禁 |

中间件根据请求 `Accept` 头自动选择 JSON 或简单 HTML 响应。

## 跳过路径与多策略路由

### 跳过路径（不走任何判定）

健康检查 / Webhook / 静态心跳类接口，可以让中间件直接放行：

```python
IP_GUARD = {
    "SKIP_PATH_PREFIXES": ["/healthz", "/internal/probe"],
}
```

### 多策略路由

通过后台或 `IpGuardPolicy` 表创建多条策略，中间件每个请求会按以下规则挑选其中一条：

1. 仅在 `enabled=True` 的策略中筛选；
2. 依次校验 `match_host_regex`、`match_path_prefixes`、`match_methods`（任一字段为空表示不限制）；
3. 按 `priority` 升序选择第一条命中；
4. 都未命中时，回退到 `name="default"` 兜底策略。

示例：仅对 `/api/admin/` 加严，并对 `api.example.com` 域名启用单独策略：

| name | priority | host_regex | path_prefixes | methods | medium_action | high_action |
|------|----------|-----------|---------------|---------|---------------|-------------|
| `admin` | 10 | `(^|.)admin\.example\.com$` | `[]` | `[]` | `block` | `ban` |
| `api-write` | 100 | `^api\.` | `[/api/]` | `["POST","PUT","DELETE"]` | `challenge` | `ban` |
| `default` | 10000 | `` | `[]` | `[]` | `block` | `ban` |

### 多 worker 失效广播

策略保存（Admin 或 `/api/policy/` API）后会通过 Redis pubsub 广播 `ip_guard:policy:invalidate`，所有 worker 在毫秒内清除自己的进程内策略缓存。无需重启即可生效。

## 自定义响应

`build_status_code` / `challenge_status_code` 直接控制响应状态码；响应体由 `services/action_executor.py` 统一构造，按请求 `Accept` 自动返回 JSON（接口）或简单 HTML（浏览器）。

## 日志记录

访问尝试会记录到 `IpAccessLog` 模型，也可以选择记录到 Django 的日志系统：

```python
LOGGING = {
    "loggers": {
        "django_ip_safeguard": {
            "handlers": ["console", "file"],
            "level": "INFO",
        },
    },
}
```

## 下一步

- [配置参考](04-configuration-reference.md) - 所有配置选项
- [数据库模型](05-models.md) - 策略和日志的数据模型
