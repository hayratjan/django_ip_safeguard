# 10 认证、CSRF、JWT 与权限模型

## 10.1 设计目标

企业控制台需要同时满足：

1. **浏览器内嵌运营**（Django Session + Cookie + CSRF）。  
2. **自动化脚本 / SPA / 移动端**（Bearer JWT，无 Session）。  
3. **细粒度权限**：不同角色仅能访问仪表盘、策略、封禁、审计等子功能。

---

## 10.2 Session 模式

1. 前端先 `GET /ip-guard/api/auth/csrf/`（`@ensure_csrf_cookie` + `@csrf_protect`）确保浏览器持有 `csrftoken`。  
2. `POST /ip-guard/api/auth/login/` 提交 `username`、`password`。  
3. 后续 POST 请求由 Axios 自动带 `X-CSRFToken`（与 Cookie 同名头）。  
4. `POST /ip-guard/api/auth/logout/` 销毁服务端会话。

**要求**：登录用户必须 **`is_staff=True`**，否则登录接口返回 403。

---

## 10.3 JWT 模式

### 10.3.1 签发与存储

- `POST /ip-guard/api/auth/jwt/login/`：校验用户名密码与 staff 后，返回 `access_token` 与 `refresh_token`（载荷与 TTL 见 `services/jwt_service.py`）。  
- access 典型用于短期 API 调用；refresh 用于换新 access。  
- 前端推荐：`localStorage` 键名由前端工程约定（如 `ip_guard_access_token`）。

### 10.3.2 校验顺序（服务端）

视图层 `_resolve_request_user`：

1. 若 `request.user` 已认证（Session），直接使用。  
2. 否则读取 `Authorization: Bearer ...`，用 **`IP_GUARD_JWT_SECRET_KEY`** 校验 JWT，解析 `sub` 为用户 ID，加载 `User`（密钥须在 settings 或环境中配置且长度 ≥32，未配置时 Bearer 校验失败，不影响未使用 JWT 的站点启动）。  
3. 将解析到的用户赋回 `request.user`，供后续 `has_perm` 使用。

### 10.3.3 刷新

- `POST /ip-guard/api/auth/jwt/refresh/`，body：`{"refresh_token":"..."}`  
- 失败返回 401，客户端应引导重新登录。

### 10.3.4 退出

- `POST /ip-guard/api/auth/jwt/logout/`：服务端无状态，**客户端删除 token** 即可；接口仍可能用于统一审计或未来黑名单扩展。

---

## 10.4 CSRF 与 JWT 并存注意

Django 的 `@csrf_protect` 对 **POST** 生效。JWT 场景下浏览器仍可能持有 CSRF Cookie（例如先访问过同源页面），故 **POST 仍建议带 CSRF 头**，与 Session 用户一致。

若纯 API 客户端（非浏览器）无 CSRF Cookie，需确保：

- 要么走 exempt（当前实现未对管理 API 全局 exempt），  
- 要么使用 Session 模式，  
- 或在同域先获取 CSRF 再带 Token——具体以你们网关策略为准。

**当前插件实现**：管理类 POST 普遍带 `@csrf_protect`，与 `frontend-admin` 联调时已按「先 GET csrf 再 POST」实现。

---

## 10.5 权限点一览

管理 API 使用 `api_permission_required` 装饰器，基于 Django 默认权限命名：

| 权限 codename | 典型用途 |
|----------------|----------|
| `django_ip_safeguard.view_ipaccesslog` | 仪表盘、审计列表、近期记录、导出 |
| `django_ip_safeguard.view_ipguardpolicy` | 策略读取、健康检查、地理池状态 |
| `django_ip_safeguard.change_ipguardpolicy` | 策略更新、地理池手动同步 |
| `django_ip_safeguard.view_ipbanrecord` | 封禁列表 |
| `django_ip_safeguard.change_ipbanrecord` | 封禁、解封 |

**建议**：在 Admin 中创建组（如「安全运营只读」「安全策略管理员」），将权限授予组，再给用户加组，避免给运营人员 `superuser`。

---

## 10.6 前端路由与菜单

`GET /ip-guard/api/auth/me/` 返回 `permissions` 数组；Vue 路由与侧边栏根据 `hasPerm('django_ip_safeguard.xxx')` 显示。

---

## 10.7 JWT 配置项（settings）

| 项 | 说明 |
|----|------|
| `IP_GUARD_JWT_SECRET_KEY` | 启用 JWT 时必填，建议 ≥32 字符随机串；未配置时进程可启动，JWT 签发/校验会报错 |
| `IP_GUARD_JWT_ALGORITHM` | 默认 `HS256` |
| `IP_GUARD_JWT_ACCESS_TTL` | access 有效期（秒） |
| `IP_GUARD_JWT_REFRESH_TTL` | refresh 有效期（秒） |

---

## 10.8 相关文档

- API 列表：[09-管理REST-API参考](./09-管理REST-API参考.md)  
- Vue 控制台：[11-Vue管理控制台使用说明](./11-Vue管理控制台使用说明.md)  
- 配置：[04-配置项完整参考](./04-配置项完整参考.md)
