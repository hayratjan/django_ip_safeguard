# Configuration Reference

## Complete Settings

All configuration options for Django IP Safeguard are set in the `IP_GUARD` dictionary in your Django settings.

```python
IP_GUARD = {
    # Core settings
    "ENABLED": True,
    "DEBUG": False,

    # IP filtering
    "WHITELIST_IPS": [],
    "BLACKLIST_IPS": [],
    "TRUSTED_PROXIES": [],

    # Default policy
    "DEFAULT_POLICY": "allow",  # or "deny"

    # ... more settings
}
```

## Core Settings

### ENABLED

- **Type**: `bool`
- **Default**: `True`
- **Description**: Enable or disable the IP guard middleware.

### DEBUG

- **Type**: `bool`
- **Default**: `False`
- **Description**: Enable debug mode for additional logging.

## IP Filtering

### WHITELIST_IPS

- **Type**: `list[str]`
- **Default**: `[]`
- **Description**: List of IP addresses or CIDR ranges that bypass all checks.

```python
IP_GUARD = {
    "WHITELIST_IPS": [
        "127.0.0.1",
        "10.0.0.0/8",
        "192.168.1.0/24",
    ],
}
```

### BLACKLIST_IPS

- **Type**: `list[str]`
- **Default**: `[]`
- **Description**: List of IP addresses or CIDR ranges that are always blocked.

### TRUSTED_PROXIES

- **Type**: `list[str]`
- **Default**: `[]`
- **Description**: List of trusted proxy IP addresses for X-Forwarded-For parsing.

### DEFAULT_POLICY

- **Type**: `str`
- **Default**: `"allow"`
- **Options**: `"allow"`, `"deny"`
- **Description**: Default policy when no rules match.

## Authentication Settings

### ENABLE_2FA

- **Type**: `bool`
- **Default**: `True`
- **Description**: Enable two-factor authentication for admin users.

### ENABLE_API_KEY

- **Type**: `bool`
- **Default**: `True`
- **Description**: Enable API key authentication.

## JWT Settings

```python
IP_GUARD = {
    "JWT": {
        "SECRET_KEY": "your-secret-key",
        "ACCESS_TOKEN_LIFETIME_MINUTES": 60,
        "REFRESH_TOKEN_LIFETIME_DAYS": 7,
        "ALGORITHM": "HS256",
    },
}
```

### JWT.SECRET_KEY

- **Type**: `str`
- **Required**: Yes
- **Description**: Secret key for JWT signing. **Change in production!**

### JWT.ACCESS_TOKEN_LIFETIME_MINUTES

- **Type**: `int`
- **Default**: `60`
- **Description**: JWT access token lifetime in minutes.

### JWT.REFRESH_TOKEN_LIFETIME_DAYS

- **Type**: `int`
- **Default**: `7`
- **Description**: JWT refresh token lifetime in days.

## Cache Settings

```python
IP_GUARD = {
    "CACHE": {
        "ENABLED": True,
        "BACKEND": "redis",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "TIMEOUT": 300,
    },
}
```

### CACHE.ENABLED

- **Type**: `bool`
- **Default**: `True`
- **Description**: Enable caching for IP lookups.

### CACHE.BACKEND

- **Type**: `str`
- **Default**: `"redis"`
- **Options**: `"redis"`, `"locmem"`, `"database"`
- **Description**: Cache backend to use.

### CACHE.LOCATION

- **Type**: `str`
- **Default**: `"redis://127.0.0.1:6379/1"`
- **Description**: Cache location (Redis URL or database table name).

### CACHE.TIMEOUT

- **Type**: `int`
- **Default**: `300`
- **Description**: Default cache timeout in seconds.

## Rate Limiting

```python
IP_GUARD = {
    "RATE_LIMIT": {
        "ENABLED": True,
        "REQUESTS_PER_MINUTE": 60,
        "BURST": 10,
    },
}
```

### RATE_LIMIT.ENABLED

- **Type**: `bool`
- **Default**: `True`
- **Description**: Enable rate limiting.

### RATE_LIMIT.REQUESTS_PER_MINUTE

- **Type**: `int`
- **Default**: `60`
- **Description**: Maximum requests per minute per IP.

## Auto Ban Settings

```python
IP_GUARD = {
    "AUTO_BAN": {
        "ENABLED": True,
        "THRESHOLD": 5,
        "DURATION_MINUTES": 30,
        "TRACK_FAILED_AUTH": True,
    },
}
```

### AUTO_BAN.ENABLED

- **Type**: `bool`
- **Default**: `True`
- **Description**: Enable automatic IP banning.

### AUTO_BAN.THRESHOLD

- **Type**: `int`
- **Default**: `5`
- **Description**: Number of failed attempts before auto-ban.

### AUTO_BAN.DURATION_MINUTES

- **Type**: `int`
- **Default**: `30`
- **Description**: Ban duration in minutes.

## Risk Engine Settings

```python
IP_GUARD = {
    "RISK_ENGINE": {
        "ENABLED": True,
        "PROVIDERS": ["local", "http"],
        "CONFIDENCE_THRESHOLD": 0.5,
    },
}
```

### RISK_ENGINE.ENABLED

- **Type**: `bool`
- **Default**: `True`
- **Description**: Enable risk assessment.

### RISK_ENGINE.PROVIDERS

- **Type**: `list[str]`
- **Default**: `["local", "http"]`
- **Description**: Risk assessment providers to use.

## GeoIP Settings

```python
IP_GUARD = {
    "GEOIP": {
        "ENABLED": True,
        "DB_PATH": "/path/to/geoip.mmdb",
        "ALLOWED_COUNTRIES": [],
        "BLOCKED_COUNTRIES": [],
    },
}
```

### GEOIP.ENABLED

- **Type**: `bool`
- **Default**: `True`
- **Description**: Enable GeoIP blocking.

### GEOIP.DB_PATH

- **Type**: `str`
- **Default**: `None`
- **Description**: Path to GeoIP database file.

### GEOIP.ALLOWED_COUNTRIES

- **Type**: `list[str]`
- **Default**: `[]`
- **Description**: List of allowed country codes (ISO 3166-1 alpha-2).

### GEOIP.BLOCKED_COUNTRIES

- **Type**: `list[str]`
- **Default**: `[]`
- **Description**: List of blocked country codes (ISO 3166-1 alpha-2).

## Threat Intelligence Settings

```python
IP_GUARD = {
    "THREAT_INTEL": {
        "ENABLED": True,
        "SUBSCRIBE_URLS": [],
        "SYNC_INTERVAL_MINUTES": 60,
    },
}
```

## Circuit Breaker Settings

```python
IP_GUARD = {
    "CIRCUIT_BREAKER": {
        "ENABLED": True,
        "FAILURE_THRESHOLD": 5,
        "RECOVERY_TIMEOUT": 60,
        "EXPECTED_EXCEPTION": "requests.exceptions.RequestException",
    },
}
```

## Block Response Settings

```python
IP_GUARD = {
    "BLOCK_RESPONSE": {
        "status_code": 403,
        "content": "Access Denied",
        "content_type": "text/plain",
    },
}
```

## Logging Settings

```python
IP_GUARD = {
    "LOGGING": {
        "ENABLED": True,
        "LEVEL": "INFO",
        "LOG_FAILED_AUTH": True,
        "LOG_BLOCKED_IPS": True,
    },
}
```

## Complete Example

```python
IP_GUARD = {
    "ENABLED": True,
    "DEBUG": False,

    "WHITELIST_IPS": ["127.0.0.1", "10.0.0.0/8"],
    "BLACKLIST_IPS": [],
    "TRUSTED_PROXIES": ["10.0.0.0/8"],
    "DEFAULT_POLICY": "allow",

    "ENABLE_2FA": True,
    "ENABLE_API_KEY": True,

    "JWT": {
        "SECRET_KEY": "change-this-in-production",
        "ACCESS_TOKEN_LIFETIME_MINUTES": 60,
        "REFRESH_TOKEN_LIFETIME_DAYS": 7,
    },

    "CACHE": {
        "ENABLED": True,
        "BACKEND": "redis",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "TIMEOUT": 300,
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

    "RISK_ENGINE": {
        "ENABLED": True,
        "PROVIDERS": ["local", "http"],
    },

    "GEOIP": {
        "ENABLED": True,
        "BLOCKED_COUNTRIES": ["CN", "RU"],
    },

    "LOGGING": {
        "ENABLED": True,
        "LEVEL": "INFO",
    },
}
```
