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
- **校验**：旧密码必须正确；新密码不少于 8 位
- **说明**：修改成功后需重新登录

### 9.9.3 `POST /ip-guard/api/auth/change-email/`

- **权限**：已登录
- **Body**：`{"new_email": "user@example.com"}`
- **校验**：邮箱格式必须合法

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

### 9.9.7 `POST /ip-guard/api/auth/2fa/disable/`

- **权限**：已登录
- **Body**：`{"code": "123456"}`
- **说明**：验证 TOTP 码后禁用 2FA，清除密钥。

---

## 9.10 用户统计图表

### 9.10.1 `GET /ip-guard/api/user-stats-chart/`

- **权限**：`django_ip_safeguard.view_ipaccesslog`
- **Query 参数**：`days`（默认 7，最大 30）
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

## 9.13 相关文档

- 认证：[10-认证CSRF-JWT与权限模型](./10-认证CSRF-JWT与权限模型.md)  
- 策略字段：[05-策略中心与数据库模型](./05-策略中心与数据库模型.md)  
- 地理池：[06-地理IP池与定时同步](./06-地理IP池与定时同步.md)
