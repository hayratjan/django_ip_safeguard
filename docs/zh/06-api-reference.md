# REST API 参考

## 概述

Django IP Safeguard 提供全面的 REST API 用于管理 IP 策略、访问日志和认证。

## 基础 URL

```
http://localhost:8000/ip-guard/api/
```

## 认证

### 会话认证

使用用户名/密码登录获取会话 cookie：

```bash
curl -X POST http://localhost:8000/ip-guard/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password123"}'
```

### JWT 认证

```bash
# 登录
curl -X POST http://localhost:8000/ip-guard/api/auth/jwt/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password123"}'

# 响应
{
  "access": "eyJ...",
  "refresh": "eyJ..."
}

# 使用令牌
curl -H "Authorization: Bearer eyJ..." http://localhost:8000/ip-guard/api/auth/me/
```

### API 密钥认证

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/ip-guard/api/dashboard/
```

## 认证 API

### POST /api/auth/login/

基于会话的登录。

**请求：**
```json
{
  "username": "admin",
  "password": "password123"
}
```

**响应 (200)：**
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

JWT 令牌登录。

**请求：**
```json
{
  "username": "admin",
  "password": "password123"
}
```

**响应 (200)：**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### POST /api/auth/jwt/refresh/

刷新 JWT 令牌。

**请求：**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**响应 (200)：**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### POST /api/auth/logout/

登出当前用户。

**响应 (200)：**
```json
{
  "success": true
}
```

### GET /api/auth/me/

获取当前认证用户。

**响应 (200)：**
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "is_staff": true
}
```

## API 密钥 API

### GET /api/auth/api-key/list/

列出用户的 API 密钥。

**响应 (200)：**
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

创建新 API 密钥。

**请求：**
```json
{
  "name": "My Application"
}
```

**响应 (201)：**
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

撤销 API 密钥。

**请求：**
```json
{
  "key_id": "ak_abc123..."
}
```

**响应 (200)：**
```json
{
  "success": true
}
```

### POST /api/auth/api-key/login/

使用 API 密钥登录。

**请求：**
```json
{
  "key": "sk_live_abc123..."
}
```

**响应 (200)：**
```json
{
  "success": true,
  "user": {
    "id": 1,
    "username": "admin"
  }
}
```

## 仪表盘 API

### GET /api/dashboard/

获取仪表盘统计。

**响应 (200)：**
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

获取最近访问记录。

**查询参数：**
- `limit` (int, 默认: 10)：记录数量
- `decision` (str)：按决策筛选 (allow/block/challenge/rate_limit)

**响应 (200)：**
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

获取用户统计数据图表。

**查询参数：**
- `days` (int, 默认: 7)：回溯天数

**响应 (200)：**
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

## 策略 API

### GET /api/policy/

获取当前 IP 策略。

**响应 (200)：**
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

更新 **默认策略**（`name="default"`）。请求体字段与 `IpGuardPolicy` ORM 对齐（含 `priority`、`match_*`、`tier_thresholds`、`signal_weights`、`medium_action`、`high_action` 等），详见安装文档「策略引擎 v2」。

保存成功后会写入 `IpGuardPolicySnapshot`（变更前 / 变更后 JSON），并通过 Redis 广播使各 worker 策略缓存失效。

### GET /api/metrics/

返回 **Redis 聚合决策计数**（中间件每次分支写入 `ip_guard:metrics:counters` HASH）以及进程内 `MetricsCollector` 摘要。需 `django_ip_safeguard.view_ipguardpolicy`。

响应 `data` 含：`redis_counters`（字段名如 `total`、`d_allow`、`d_block`、`b_blacklist`、`b_risk`、`a_ban`、`p_default`…）、`in_process_summary`、`metrics_redis_enabled`、`structured_decision_logging`。

### POST /api/metrics/reset/

清空 Redis 决策计数 HASH。需 `django_ip_safeguard.change_ipguardpolicy`。

### GET /api/policies/

列出全部策略行摘要（`name`、`priority`、`enabled`、`medium_action`、`high_action`、`updated_at`）。

### POST /api/policies/

新建策略行，JSON：`{"name":"my-api"}`（名称仅允许 `[\w.-]+`，最长 64）。

### `GET/POST /api/policies/<name>/`

按策略名读写单行策略；POST 行为与 ``POST /api/policy/`` 相同（含快照）。

### GET /api/policy/snapshots/

分页快照列表。查询参数：`policy`（策略名）、`page`、`page_size`（最大 100）。

### `POST /api/policy/snapshots/<id>/rollback/`

将对应策略 **恢复为该快照记录中的「变更前」字段**（即 `before_json`）。需 `change_ipguardpolicy`；成功后再写一条新快照。

## 封禁管理 API

### POST /api/ban/

封禁 IP 地址。

**请求：**
```json
{
  "ip_address": "192.168.1.100",
  "reason": "暴力破解攻击",
  "duration_minutes": 60
}
```

**响应 (200)：**
```json
{
  "success": true,
  "ip_address": "192.168.1.100",
  "expires_at": "2024-01-15T13:00:00Z"
}
```

### POST /api/unban/

解封 IP 地址。

**请求：**
```json
{
  "ip_address": "192.168.1.100"
}
```

**响应 (200)：**
```json
{
  "success": true
}
```

### GET /api/ban-list/

列出当前已封禁的 IP。

**查询参数：**
- `page` (int)：页码
- `page_size` (int)：每页数量

**响应 (200)：**
```json
{
  "items": [
    {
      "ip_address": "192.168.1.100",
      "reason": "暴力破解攻击",
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

## 访问日志 API

### GET /api/access-logs/

分页查询审计日志（与 [09-管理REST-API参考](../09-管理REST-API参考.md) 一致；实际部署前缀多为 `/ip-guard/api/`）。

**查询参数：**
- `page`、`page_size`
- `decision`：`allow` / `block`
- `country`：ISO2 国家码
- `path`：路径子串
- `q`：IP 子串
- `username`：用户名子串（模糊）
- `user_id`：Django 用户 ID（精确）
- `start`、`end`：日期 `YYYY-MM-DD`

**响应 `items[]` 字段（节选）：** `ip`、`user_id`、`username`、`method`、`country_code`、`country_name`、`region`、`city`、`risk_score`、`risk_tags`、`decision`、`reason`、`path`、`created_at`。

### GET /api/access-logs/export/

流式导出 CSV（UTF-8 BOM），筛选参数同上，最多 10000 条。

### GET /api/access-logs/user-summary/

按用户汇总：`user_id`（必填）、`days`（默认 30，最大 180）。返回访问总数、全量不同 IP 数、`by_ip` 列表（至多 200 行，按次数降序）及每条 IP 最近日志上的地理信息。

## 健康检查 API

### GET /api/health/

系统健康检查。

**响应 (200)：**
```json
{
  "status": "healthy",
  "database": "ok",
  "cache": "ok",
  "version": "0.1.0"
}
```

## 双因素认证 API

### GET /api/auth/2fa/status/

获取 2FA 状态。

**响应 (200)：**
```json
{
  "enabled": false,
  "methods": ["totp"]
}
```

### POST /api/auth/2fa/setup/

设置 2FA。

**响应 (200)：**
```json
{
  "secret": "JBSWY3DPEHPK3PXP",
  "otpauth_url": "otpauth://totp/Example:admin?secret=JBSWY3DPEHPK3PXP&issuer=Example",
  "qr_code": "data:image/png;base64,..."
}
```

### POST /api/auth/2fa/verify/

验证 2FA 码。

**请求：**
```json
{
  "code": "123456"
}
```

**响应 (200)：**
```json
{
  "success": true
}
```

### POST /api/auth/2fa/disable/

禁用 2FA。

**请求：**
```json
{
  "password": "current_password",
  "code": "123456"
}
```

## 计划任务 API

### GET /api/scheduled-tasks/

列出计划任务。

**响应 (200)：**
```json
{
  "items": [
    {
      "id": 1,
      "name": "每日 GeoIP 同步",
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

立即运行计划任务。

**响应 (200)：**
```json
{
  "success": true,
  "execution_id": 123
}
```

## 错误响应

### 400 Bad Request

```json
{
  "error": "validation_error",
  "message": "输入无效",
  "details": {
    "field": ["错误信息"]
  }
}
```

### 401 Unauthorized

```json
{
  "error": "authentication_required",
  "message": "需要认证"
}
```

### 403 Forbidden

```json
{
  "error": "permission_denied",
  "message": "您没有权限执行此操作"
}
```

### 404 Not Found

```json
{
  "error": "not_found",
  "message": "资源未找到"
}
```

### 429 Too Many Requests

```json
{
  "error": "rate_limit_exceeded",
  "message": "请求过于频繁，请稍后再试",
  "retry_after": 60
}
```
