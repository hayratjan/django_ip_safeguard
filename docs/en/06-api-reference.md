# REST API Reference

## Overview

Django IP Safeguard provides a comprehensive REST API for managing IP policies, accessing logs, and authentication.

## Base URL

```
http://localhost:8000/ip-guard/api/
```

## Authentication

### Session Authentication

Login with username/password to get session cookie:

```bash
curl -X POST http://localhost:8000/ip-guard/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password123"}'
```

### JWT Authentication

```bash
# Login
curl -X POST http://localhost:8000/ip-guard/api/auth/jwt/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password123"}'

# Response
{
  "access": "eyJ...",
  "refresh": "eyJ..."
}

# Use token
curl -H "Authorization: Bearer eyJ..." http://localhost:8000/ip-guard/api/auth/me/
```

### API Key Authentication

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/ip-guard/api/dashboard/
```

## Authentication API

### POST /api/auth/login/

Session-based login.

**Request:**
```json
{
  "username": "admin",
  "password": "password123"
}
```

**Response (200):**
```json
{
  "success": true,
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com"
  }
}
```

### POST /api/auth/jwt/login/

JWT token login.

**Request:**
```json
{
  "username": "admin",
  "password": "password123"
}
```

**Response (200):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### POST /api/auth/jwt/refresh/

Refresh JWT token.

**Request:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response (200):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### POST /api/auth/logout/

Logout current user.

**Response (200):**
```json
{
  "success": true
}
```

### GET /api/auth/me/

Get current authenticated user.

**Response (200):**
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "is_staff": true
}
```

## API Key API

### GET /api/auth/api-key/list/

List user's API keys.

**Response (200):**
```json
{
  "items": [
    {
      "id": 1,
      "name": "My App",
      "key_id": "ak_abc123...",
      "created_at": "2024-01-01T00:00:00Z",
      "last_used_at": "2024-01-15T12:00:00Z",
      "is_active": true
    }
  ]
}
```

### POST /api/auth/api-key/create/

Create new API key.

**Request:**
```json
{
  "name": "My Application"
}
```

**Response (201):**
```json
{
  "id": 1,
  "name": "My Application",
  "key": "sk_live_abc123...",
  "key_id": "ak_abc123...",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### POST /api/auth/api-key/revoke/

Revoke an API key.

**Request:**
```json
{
  "key_id": "ak_abc123..."
}
```

**Response (200):**
```json
{
  "success": true
}
```

### POST /api/auth/api-key/login/

Login using API key.

**Request:**
```json
{
  "key": "sk_live_abc123..."
}
```

**Response (200):**
```json
{
  "success": true,
  "user": {
    "id": 1,
    "username": "admin"
  }
}
```

## Dashboard API

### GET /api/dashboard/

Get dashboard statistics.

**Response (200):**
```json
{
  "total_banned": 150,
  "total_access": 10000,
  "blocked_today": 25,
  "recent_logs": [...],
  "top_blocked_ips": [...]
}
```

### GET /api/recent-records/

Get recent access records.

**Query Parameters:**
- `limit` (int, default: 10): Number of records
- `decision` (str): Filter by decision (allow/block/challenge/rate_limit)

**Response (200):**
```json
{
  "items": [
    {
      "id": 1,
      "ip_address": "192.168.1.1",
      "path": "/admin/",
      "method": "GET",
      "decision": "allow",
      "created_at": "2024-01-15T12:00:00Z"
    }
  ]
}
```

### GET /api/user-stats-chart/

Get user statistics for charts.

**Query Parameters:**
- `days` (int, default: 7): Number of days to look back

**Response (200):**
```json
{
  "hourly_pattern": [
    {"hour": "00:00", "total": 100, "blocked": 5},
    {"hour": "01:00", "total": 80, "blocked": 3}
  ],
  "daily_stats": [
    {"date": "2024-01-01", "total": 500, "blocked": 20}
  ]
}
```

## Policy API

### GET /api/policy/

Get current IP policy.

**Response (200):**
```json
{
  "name": "Default Policy",
  "is_active": true,
  "ip_whitelist": ["127.0.0.1"],
  "ip_blacklist": [],
  "rate_limit_enabled": true,
  "rate_limit_requests": 60,
  "geoip_enabled": true,
  "blocked_countries": ["CN", "RU"]
}
```

### POST /api/policy/

Updates the **default policy** (`name="default"`). Request body fields align with the `IpGuardPolicy` ORM (including `priority`, `match_*`, `tier_thresholds`, `signal_weights`, `medium_action`, `high_action`, etc.); see the installation guide section **Policy engine v2**.

On success, writes an `IpGuardPolicySnapshot` (before/after JSON) and broadcasts via Redis so worker policy caches are invalidated.

**Request (example):**
```json
{
  "rate_limit_enabled": true,
  "rate_limit_requests": 100,
  "blocked_countries": ["CN"]
}
```

### GET /api/metrics/

Returns **Redis aggregated decision counters** (each middleware branch increments `ip_guard:metrics:counters` HASH) plus an in-process `MetricsCollector` summary. Requires `django_ip_safeguard.view_ipguardpolicy`.

Response `data` includes: `redis_counters` (fields such as `total`, `d_allow`, `d_block`, `b_blacklist`, `b_risk`, `a_ban`, `p_default`, …), `in_process_summary`, `metrics_redis_enabled`, `structured_decision_logging`.

### POST /api/metrics/reset/

Clears the Redis decision-counter HASH. Requires `django_ip_safeguard.change_ipguardpolicy`.

### GET /api/policies/

Lists summary rows for all policies (`name`, `priority`, `enabled`, `medium_action`, `high_action`, `updated_at`).

### POST /api/policies/

Creates a new policy row. JSON: `{"name":"my-api"}` (name must match `[\w.-]+`, max length 64).

### `GET/POST /api/policies/<name>/`

Reads or writes a single policy by name; `POST` behaves like `POST /api/policy/` (including snapshots).

### GET /api/policy/snapshots/

Paginated snapshot list. Query parameters: `policy` (policy name), `page`, `page_size` (max 100).

### `POST /api/policy/snapshots/<id>/rollback/`

Restores that policy **to the snapshot’s “before” fields** (`before_json`). Requires `change_ipguardpolicy`; on success writes a new snapshot row.

## Ban Management API

### POST /api/ban/

Ban an IP address.

**Request:**
```json
{
  "ip_address": "192.168.1.100",
  "reason": "Brute force attack",
  "duration_minutes": 60
}
```

**Response (200):**
```json
{
  "success": true,
  "ip_address": "192.168.1.100",
  "expires_at": "2024-01-15T13:00:00Z"
}
```

### POST /api/unban/

Unban an IP address.

**Request:**
```json
{
  "ip_address": "192.168.1.100"
}
```

**Response (200):**
```json
{
  "success": true
}
```

### GET /api/ban-list/

List currently banned IPs.

**Query Parameters:**
- `page` (int): Page number
- `page_size` (int): Items per page

**Response (200):**
```json
{
  "items": [
    {
      "ip_address": "192.168.1.100",
      "reason": "Brute force attack",
      "banned_at": "2024-01-15T12:00:00Z",
      "expires_at": "2024-01-15T13:00:00Z",
      "banned_by": "admin"
    }
  ],
  "pagination": {
    "total": 150,
    "page": 1,
    "page_size": 20
  }
}
```

## Access Logs API

### GET /api/access-logs/

Get access logs.

**Query Parameters:**
- `page` (int): Page number
- `page_size` (int): Items per page
- `ip_address` (str): Filter by IP
- `decision` (str): Filter by decision
- `start_date` (str): Filter by start date (ISO format)
- `end_date` (str): Filter by end date (ISO format)

**Response (200):**
```json
{
  "items": [
    {
      "id": 1,
      "ip_address": "192.168.1.1",
      "path": "/admin/",
      "method": "GET",
      "status_code": 200,
      "decision": "allow",
      "country": "US",
      "created_at": "2024-01-15T12:00:00Z"
    }
  ],
  "pagination": {
    "total": 10000,
    "page": 1,
    "page_size": 20
  }
}
```

### GET /api/access-logs/export/

Export access logs.

**Query Parameters:**
- Same as GET /api/access-logs/
- `format` (str): Export format (csv/json)

**Response (200):**
File download

## Health Check API

### GET /api/health/

System health check.

**Response (200):**
```json
{
  "status": "healthy",
  "database": "ok",
  "cache": "ok",
  "version": "0.1.0"
}
```

## Two-Factor Authentication API

### GET /api/auth/2fa/status/

Get 2FA status.

**Response (200):**
```json
{
  "enabled": false,
  "methods": ["totp"]
}
```

### POST /api/auth/2fa/setup/

Setup 2FA.

**Response (200):**
```json
{
  "secret": "JBSWY3DPEHPK3PXP",
  "otpauth_url": "otpauth://totp/Example:admin?secret=JBSWY3DPEHPK3PXP&issuer=Example",
  "qr_code": "data:image/png;base64,..."
}
```

### POST /api/auth/2fa/verify/

Verify 2FA code.

**Request:**
```json
{
  "code": "123456"
}
```

**Response (200):**
```json
{
  "success": true
}
```

### POST /api/auth/2fa/disable/

Disable 2FA.

**Request:**
```json
{
  "password": "current_password",
  "code": "123456"
}
```

## Scheduled Tasks API

### GET /api/scheduled-tasks/

List scheduled tasks.

**Response (200):**
```json
{
  "items": [
    {
      "id": 1,
      "name": "Daily GeoIP Sync",
      "task_type": "sync_geo_ip",
      "cron_expression": "0 2 * * *",
      "is_active": true,
      "last_run_at": "2024-01-15T02:00:00Z",
      "next_run_at": "2024-01-16T02:00:00Z"
    }
  ]
}
```

### POST /api/scheduled-tasks/<id>/run/

Run a scheduled task immediately.

**Response (200):**
```json
{
  "success": true,
  "execution_id": 123
}
```

## Error Responses

### 400 Bad Request

```json
{
  "error": "validation_error",
  "message": "Invalid input",
  "details": {
    "field": ["Error message"]
  }
}
```

### 401 Unauthorized

```json
{
  "error": "authentication_required",
  "message": "Authentication required"
}
```

### 403 Forbidden

```json
{
  "error": "permission_denied",
  "message": "You don't have permission to perform this action"
}
```

### 404 Not Found

```json
{
  "error": "not_found",
  "message": "Resource not found"
}
```

### 429 Too Many Requests

```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Try again later.",
  "retry_after": 60
}
```
