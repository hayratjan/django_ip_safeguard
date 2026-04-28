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

### Policy Actions (v0.2.0)

| Action | HTTP Status | Bans IP? | Description |
|--------|-------------|----------|-------------|
| `allow` | 200 | no | Pass through |
| `log_only` | 200 | no | Just log, behave like allow (great for canary roll-out) |
| `rate_limit` | 429 | no | Soft throttle (matches `rate_limit_per_minute` semantics) |
| `challenge` | `challenge_status_code` (default 403) | no | Returns custom status for CAPTCHA / 2FA flows |
| `block` | `block_status_code` (default 403) | no | Reject the request |
| `ban` | `block_status_code` | yes (`ban_ttl`) | Reject and write a Redis ban entry |

The middleware honours the `Accept` request header and returns either JSON (APIs) or a tiny HTML page (browsers).

## Skip paths and multi-policy routing

### Skip paths

Health checks / webhooks / probes can bypass IP Guard entirely:

```python
IP_GUARD = {
    "SKIP_PATH_PREFIXES": ["/healthz", "/internal/probe"],
}
```

### Multi-policy routing

Create multiple `IpGuardPolicy` rows. Per request the middleware:

1. Filters disabled policies;
2. Checks `match_host_regex`, `match_path_prefixes`, `match_methods` (empty means "no constraint");
3. Picks the lowest-priority match;
4. Falls back to `name="default"` when no row matches.

Policy saves are broadcast through Redis pubsub (`ip_guard:policy:invalidate`); every worker drops its cache within milliseconds.

## Custom Response

`block_status_code` and `challenge_status_code` directly control the HTTP status. The body is built by `services/action_executor.py` based on the request `Accept` header.

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
