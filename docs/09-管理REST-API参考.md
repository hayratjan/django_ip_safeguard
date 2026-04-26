# 09 管理 REST API 参考

## 9.1 通用约定

### 9.1.1 URL 前缀

假设项目在根 `urls.py` 中挂载为：

```python
path("ip-guard/", include("django_ip_safeguard.urls")),
```

则本文档中所有路径均以 **`/ip-guard/`** 为前缀。若你使用其它前缀，请自行替换。

### 9.1.2 统一 JSON 封装（除 CSV 导出外）

成功示例：

```json
{
  "code": 0,
  "message": "ok",
  "data": { }
}
```

失败示例：

```json
{
  "code": 4000,
  "message": "错误说明",
  "data": {}
}
```

前端 Axios 封装若已解包为 `data` 字段，请以实际前端代码为准（参见 [11](./11-Vue管理控制台使用说明.md)）。

### 9.1.3 鉴权与权限

- 绝大多数管理接口要求：**已认证**且 **`is_staff=True`**，并校验 **Django 模型权限**（见 [10](./10-认证CSRF-JWT与权限模型.md)）。  
- **CSRF**：除少数 GET 下发 Cookie 的接口外，**POST 等变更类接口**均带 `@csrf_protect`，浏览器场景需携带 `csrftoken` Cookie 与 `X-CSRFToken` 头。  
- **JWT**：请求头 `Authorization: Bearer <access_token>`；服务端通过 `get_user_from_access_token` 解析用户后再做 `has_perm` 判断。

### 9.1.4 HTTP 动词概览

| 方法 | 典型用途 |
|------|----------|
| GET | 查询、列表、健康检查 |
| POST | 登录、改策略、封禁、同步池、解封等 |

---

## 9.2 认证与用户

| 路径 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/ip-guard/api/auth/csrf/` | GET | 无（会设 CSRF Cookie） | 确保浏览器获得 `csrftoken` |
| `/ip-guard/api/auth/login/` | POST | 无 | JSON body：`username`、`password`；成功建立 Session |
| `/ip-guard/api/auth/logout/` | POST | 已登录 | Session 登出 |
| `/ip-guard/api/auth/me/` | GET | 已登录 staff | 返回 `username`、`groups`、`permissions` 等 |
| `/ip-guard/api/auth/jwt/login/` | POST | 无 | body 同登录；返回 `access_token`、`refresh_token` 等 |
| `/ip-guard/api/auth/jwt/refresh/` | POST | 无 | body：`refresh_token`；返回新 `access_token` |
| `/ip-guard/api/auth/jwt/logout/` | POST | 无 | 无状态提示，客户端删 token |

**登录成功**（Session）`data` 示例：`{"username": "..."}`  
**JWT 登录成功** `data` 内含 `access_token`、`refresh_token`、`expires_in` 等（以实际视图返回为准）。

---

## 9.3 运营与统计

### 9.3.1 `GET /ip-guard/api/dashboard/`

- **权限**：`django_ip_safeguard.view_ipaccesslog`  
- **说明**：约 24 小时窗口的运营统计：总量、拦截率、国家分布、热门路径、拦截原因 Top、按小时趋势等（字段以实际接口为准）。

### 9.3.2 `GET /ip-guard/api/recent-records/`

- **权限**：`view_ipaccesslog` **或** `view_ipbanrecord`（满足其一即可，`any_perm=True`）  
- **Query 参数**：
  - `days`：统计天数，默认 `7`，最大 `30`
  - `attack_limit`：返回最近拦截记录条数，默认 `100`，最大 `200`
  - `access_limit`：返回最近访问（含放行）条数，默认 `100`，最大 `200`
  - `ban_limit`：返回近期封禁条数，默认 `40`，最大 `100`
- **说明**：包含按日 `allow`/`block` 汇总、样本列表、封禁样本等。

---

## 9.4 策略中心

### 9.4.1 `GET /ip-guard/api/policy/`

- **权限**：`view_ipguardpolicy`  
- **说明**：返回默认策略全部可读字段，含 `china_pool_rule`、`international_pool_rule`、`pool_feed_urls`（数据源 URL 只读说明）等。

### 9.4.2 `POST /ip-guard/api/policy/`

- **权限**：`change_ipguardpolicy`  
- **Body**：JSON，仅提交需要修改的字段即可（未出现字段保持不变）。  
- **数组类字段**：`blocked_risk_tags`、`allowed_countries`、`blocked_countries`、`ip_whitelist`、`ip_blacklist`、`fail_open_path_prefixes`、`fail_close_path_prefixes`  
- **校验**：国家码须为两位字母；IP/CIDR 须合法；`rate_limit_per_minute` 为 `0～100000`；地理池规则仅 `off` / `allow_only_in_pool` / `block_in_pool`。

---

## 9.5 地理 IP 池

### 9.5.1 `GET /ip-guard/api/geo-pools/status/`

- **权限**：`view_ipguardpolicy`  
- **说明**：返回各池同步元数据（`IpGeoPoolStatus`）、`feed_urls`、`rule_choices` 等。

### 9.5.2 `POST /ip-guard/api/geo-pools/sync/`

- **权限**：`change_ipguardpolicy`  
- **说明**：触发 `sync_all_geo_pools`；`data.results` 为各池执行结果列表（含 `skipped` 的国际池跳过说明）。

---

## 9.6 封禁管理

### 9.6.1 `POST /ip-guard/api/ban/`

- **权限**：`change_ipbanrecord`  
- **Body**：`{"ip":"1.2.3.4","reason":"可选","ttl":86400}`，`ttl` 最小 60 秒。

### 9.6.2 `POST /ip-guard/api/unban/`

- **权限**：`change_ipbanrecord`  
- **Body**：`{"ip":"1.2.3.4"}`

### 9.6.3 `GET /ip-guard/api/ban-list/`

- **权限**：`view_ipbanrecord`  
- **Query**：`page`（默认 1）、`page_size`（默认 20，有上下限）、`active`=`true`/`false`、`q`（IP 模糊）、`source`（封禁来源精确）

---

## 9.7 审计日志

### 9.7.1 `GET /ip-guard/api/access-logs/`

- **权限**：`view_ipaccesslog`  
- **Query**：`page`、`page_size`；筛选：`decision`=`allow|block`、`country`（ISO2）、`path`（子串）、`q`（IP 子串）、`start`/`end`（`YYYY-MM-DD`）

### 9.7.2 `GET /ip-guard/api/access-logs/export/`

- **权限**：`view_ipaccesslog`  
- **说明**：**流式 CSV**；与列表接口相同筛选条件；**最多 10000 条**；带 UTF-8 BOM。  
- **鉴权**：Session Cookie；JWT 场景需在 HTTP 客户端上附加 `Authorization: Bearer`（前端导出模块已对齐）。

---

## 9.8 健康检查

### 9.8.1 `GET /ip-guard/api/health/`

- **权限**：`view_ipguardpolicy`  
- **说明**：`redis_ok`、`redis_latency_ms`、`provider`、`policy_center_enabled`、`provider_circuit_failures`、`geo_ip_pools`（同步摘要）、`geo_pool_feed_urls` 等。

---

## 9.9 用户管理

### 9.9.1 `GET /ip-guard/api/auth/profile/`

- **权限**：已登录
- **说明**：返回当前用户信息，包括 `username`、`email`、`is_superuser`、`is_staff`、`two_factor_enabled`、`date_joined`、`last_login`

### 9.9.2 `POST /ip-guard/api/auth/change-password/`

- **权限**：已登录
- **Body**：`{"old_password": "...", "new_password": "..."}`
- **校验**：旧密码必须正确；新密码不少于 8 位；新密码需包含大写字母、小写字母、数字、特殊字符中的至少 3 种
- **审计**：修改成功后自动记录安全审计日志（`password_change`）
- **说明**：修改成功后需重新登录

### 9.9.3 `POST /ip-guard/api/auth/change-email/`

- **权限**：已登录
- **Body**：`{"new_email": "user@example.com"}`
- **校验**：邮箱格式必须合法
- **审计**：修改成功后自动记录安全审计日志（`email_change`）

### 9.9.4 `GET /ip-guard/api/auth/2fa/status/`

- **权限**：已登录
- **说明**：返回 `{"enabled": true/false, "has_secret": true/false}`

### 9.9.5 `POST /ip-guard/api/auth/2fa/setup/`

- **权限**：已登录
- **说明**：生成 TOTP 密钥，返回 `{"secret": "...", "provisioning_uri": "otpauth://totp/..."}`。依赖 `pyotp` 包。

### 9.9.6 `POST /ip-guard/api/auth/2fa/verify/`

- **权限**：已登录
- **Body**：`{"code": "123456"}`
- **说明**：验证 TOTP 码并启用 2FA。验证成功后 `two_factor_secret` 写入用户模型。
- **审计**：启用成功后自动记录安全审计日志（`2fa_enable`）

### 9.9.7 `POST /ip-guard/api/auth/2fa/disable/`

- **权限**：已登录
- **Body**：`{"code": "123456"}`
- **说明**：验证 TOTP 码后禁用 2FA，清除密钥。
- **审计**：禁用成功后自动记录安全审计日志（`2fa_disable`）

---

### 9.9.8 `POST /ip-guard/api/auth/2fa/login-verify/`

- **权限**：无需登录（需先完成用户名密码登录步骤）
- **Body**：`{"code": "123456", "login_mode": "session|jwt"}`
- **说明**：2FA 登录验证端点。当用户启用了 2FA 时，登录接口会返回 `{"2fa_required": true}`，前端需引导用户输入 TOTP 验证码后调用此接口完成登录。
- **超时**：2FA 验证窗口为 5 分钟（300 秒），超时后需重新登录
- **返回**：
  - Session 模式：`{"username": "..."}`，设置 session cookie
  - JWT 模式：`{"access_token": "...", "refresh_token": "..."}`

---

## 9.10 用户统计图表

### 9.10.1 `GET /ip-guard/api/user-stats-chart/`

- **权限**：`django_ip_safeguard.view_ipaccesslog`
- **Query 参数**：`days`（默认 7，最大 30）
- **缓存**：Redis 缓存 5 分钟（key: `chart:stats:{days}`），缓存不可用时自动降级为直接查询
- **说明**：返回四组图表数据：
  - `daily_trend`：按日统计 `allow`/`block` 数量
  - `risk_distribution`：高/中/低风险占比
  - `hourly_pattern`：24 小时请求和拦截分布
  - `top_countries`：访问量 Top10 国家

---

## 9.11 系统设置

### 9.11.1 `GET /ip-guard/api/system-settings/`

- **权限**：`view_ipguardpolicy`
- **说明**：返回当前策略配置和地理池规则

### 9.11.2 `POST /ip-guard/api/system-settings/`

- **权限**：`change_ipguardpolicy`
- **Body**：JSON，仅提交需修改的字段：
  - `use_db_log`：布尔，是否启用数据库审计日志
  - `fail_open`：布尔，全局失败放行
  - `block_status_code`：整数（400-499），拦截 HTTP 状态码
  - `rate_limit_per_minute`：整数（0-100000），每分钟请求上限
  - `risk_score_threshold`：整数（0-100），风险阈值
  - `cache_ttl`：整数（≥60），情报缓存 TTL（秒）
  - `ban_ttl`：整数（≥60），封禁 TTL（秒）
  - `china_pool_rule`：`off`/`allow_only_in_pool`/`block_in_pool`
  - `international_pool_rule`：`off`/`allow_only_in_pool`/`block_in_pool`

---

## 9.12 典型错误码（节选）

| code | HTTP | 含义（示例） |
|------|------|----------------|
| 0 | 200 | 成功 |
| 4001 | 400 | JSON 无法解析 |
| 4003～4012 | 400 | 参数校验类（见接口实现） |
| 4010 | 401 | 未登录或登录过期 |
| 4030 | 403 | 非 staff |
| 4031 | 403 | 缺少所需权限点 |

完整列表以 `views.py` 中 `api_error(..., code=...)` 为准。

---

## 9.13 定时任务管理

### 9.13.1 `GET /ip-guard/api/scheduled-tasks/`

- **权限**：`view_scheduledtask`
- **说明**：获取定时任务列表，支持分页和过滤
- **Query 参数**：
  - `page`：页码，默认 `1`
  - `page_size`：每页条数，默认 `20`
  - `enabled`：筛选启用状态（`true`/`false`）
  - `task_type`：筛选任务类型（如 `geoip2_update`）
- **返回**：
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": 1,
        "name": "GeoIP2数据库更新",
        "task_type": "geoip2_update",
        "task_type_display": "GeoIP2 数据库更新",
        "command": "",
        "cron_expression": "",
        "cron_preset": "@monthly",
        "cron_preset_display": "每月",
        "interval_minutes": 0,
        "schedule_display": "每月",
        "enabled": true,
        "description": "自动更新 GeoIP2 数据库",
        "last_run_at": "2026-04-01T03:00:00",
        "last_run_status": "success",
        "last_run_output": "",
        "next_run_at": "2026-05-01T03:00:00",
        "run_count": 4,
        "success_count": 4,
        "failure_count": 0,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-04-01T03:00:00"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total": 4,
      "num_pages": 1
    }
  }
}
```

### 9.13.2 `POST /ip-guard/api/scheduled-tasks/`

- **权限**：`add_scheduledtask`
- **说明**：创建新的定时任务
- **Body**：
```json
{
  "name": "自定义任务",
  "task_type": "custom",
  "cron_preset": "@daily",
  "enabled": true,
  "description": "这是一个自定义任务",
  "command": "sync_geo_ip_pools --force"
}
```
- **任务类型说明**：
  - `geoip2_update`：GeoIP2 数据库更新
  - `threat_intel_sync`：威胁情报同步
  - `ip_reputation_snapshot`：IP 信誉快照
  - `geo_pool_sync`：地理IP池同步
  - `custom`：自定义命令
- **调度方式**：
  - `cron_preset`：预设周期（`@hourly`/`@daily`/`@weekly`/`@monthly`）
  - `cron_expression`：自定义 Cron 表达式（如 `0 3 * * *`）
  - `interval_minutes`：执行间隔分钟数（与 Cron 二选一）

### 9.13.3 `GET /ip-guard/api/scheduled-tasks/<task_id>/`

- **权限**：`view_scheduledtask`
- **说明**：获取单个定时任务详情

### 9.13.4 `PUT /ip-guard/api/scheduled-tasks/<task_id>/`

- **权限**：`change_scheduledtask`
- **说明**：更新定时任务配置
- **Body**：同创建，仅提交需修改的字段

### 9.13.5 `DELETE /ip-guard/api/scheduled-tasks/<task_id>/`

- **权限**：`delete_scheduledtask`
- **说明**：删除定时任务

### 9.13.6 `POST /ip-guard/api/scheduled-tasks/<task_id>/run/`

- **权限**：`change_scheduledtask`
- **说明**：手动触发任务立即执行

---

## 9.14 相关文档
- 认证：[10-认证CSRF-JWT与权限模型](./10-认证CSRF-JWT与权限模型.md)  
- 策略字段：[05-策略中心与数据库模型](./05-策略中心与数据库模型.md)  
- 地理池：[06-地理IP池与定时同步](./06-地理IP池与定时同步.md)
