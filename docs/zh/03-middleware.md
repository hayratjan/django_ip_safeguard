# 中间件与请求流程

## 概述

`IpGuardMiddleware` 是 Django IP Safeguard 的核心组件。它拦截所有传入的 HTTP 请求并根据配置的安全策略进行评估。

## 请求处理流程

```
传入请求
    │
    ▼
┌───────────────────┐
│  检查是否启用      │
└───────────────────┘
    │
    ▼ (启用)
┌───────────────────┐
│  获取客户端 IP     │
└───────────────────┘
    │
    ▼
┌───────────────────┐
│  检查白名单        │─────────── 允许（通过）
└───────────────────┘
    │
    ▼ (不在白名单)
┌───────────────────┐
│  检查黑名单        │─────────── 阻止（403 Forbidden）
└───────────────────┘
    │
    ▼ (不在黑名单)
┌───────────────────┐
│  限流检查         │─────────── 阻止（429 Too Many）
└───────────────────┘
    │
    ▼ (允许)
┌───────────────────┐
│  风险评估         │
│  (威胁情报)       │
└───────────────────┘
    │
    ▼
┌───────────────────┐
│  GeoIP 检查       │
│  (国家规则)       │
└───────────────────┘
    │
    ▼
┌───────────────────┐
│  执行策略         │
│  (允许/阻止)      │
└───────────────────┘
    │
    ▼
┌───────────────────┐
│  记录访问日志     │
└───────────────────┘
    │
    ▼
    继续处理
    下一个中间件
```

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

### 策略动作

| 动作 | HTTP 状态 | 描述 |
|------|----------|------|
| allow | 200 | 请求允许，继续处理 |
| block | 403 | 请求被阻止 |
| challenge | 403 | 带验证码/挑战的阻止 |
| rate_limit | 429 | 请求过多 |

## 自定义响应

可以自定义被阻止时的响应：

```python
IP_GUARD = {
    "BLOCK_RESPONSE": {
        "status_code": 403,
        "content": "您的 IP 已被阻止",
        "content_type": "text/plain",
    }
}
```

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
