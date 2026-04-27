# Middleware & Request Flow

## Overview

The `IpGuardMiddleware` is the core component of Django IP Safeguard. It intercepts all incoming HTTP requests and evaluates them against configured security policies.

## Request Processing Flow

```
Incoming Request
        │
        ▼
┌───────────────────┐
│  Check if enabled │
└───────────────────┘
        │
        ▼ (enabled)
┌───────────────────┐
│  Get client IP    │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  Check whitelist  │─────────── Allow (pass through)
└───────────────────┘
        │
        ▼ (not in whitelist)
┌───────────────────┐
│  Check blacklist  │─────────── Block (403 Forbidden)
└───────────────────┘
        │
        ▼ (not in blacklist)
┌───────────────────┐
│  Rate limit check │─────────── Block (429 Too Many)
└───────────────────┘
        │
        ▼ (allowed)
┌───────────────────┐
│  Risk assessment  │
│  (threat intel)   │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  GeoIP check      │
│  (country rules)  │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  Execute policy   │
│  (allow/block)    │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  Log access       │
└───────────────────┘
        │
        ▼
    Continue to
    next middleware
```

## Middleware Configuration

### Basic Configuration

```python
# settings.py
IP_GUARD = {
    "ENABLED": True,
    "WHITELIST_IPS": ["127.0.0.1", "10.0.0.0/8"],
    "BLACKLIST_IPS": ["192.168.1.100"],
    "DEFAULT_POLICY": "allow",
}
```

### Middleware Order

The middleware should be placed early in the middleware stack to intercept requests before they reach your views:

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django_ip_safeguard.middleware.IpGuardMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # ... other middleware
]
```

## IP Address Detection

The middleware automatically detects the client IP address, considering:

1. `X-Forwarded-For` header (for proxied requests)
2. `X-Real-IP` header
3. `REMOTE_ADDR` server variable

### Trusted Proxies

```python
IP_GUARD = {
    "TRUSTED_PROXIES": ["10.0.0.0/8", "172.16.0.0/12"],
}
```

## Policy Evaluation

### Policy Priority

1. Whitelist IPs (always allowed)
2. Blacklist IPs (always blocked)
3. Rate limit rules
4. Risk assessment results
5. GeoIP rules
6. Default policy

### Policy Actions

| Action | HTTP Status | Description |
|--------|-------------|-------------|
| allow | 200 | Request allowed, continue processing |
| block | 403 | Request blocked with Forbidden |
| challenge | 403 | Blocked with CAPTCHA/challenge |
| rate_limit | 429 | Too many requests |

## Custom Response

You can customize the blocked response:

```python
IP_GUARD = {
    "BLOCK_RESPONSE": {
        "status_code": 403,
        "content": "Your IP has been blocked",
        "content_type": "text/plain",
    }
}
```

## Logging

Access attempts are logged to the `IpAccessLog` model and optionally to Django's logging system:

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

## Next Steps

- [Configuration Reference](04-configuration-reference.md) - All configuration options
- [Database Models](05-models.md) - Data models for policies and logs
