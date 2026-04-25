# 11 Vue 管理控制台使用说明

## 11.1 工程位置与技术栈

- 目录：`frontend-admin/`  
- 框架：**Vue 3** + **Vite 5** + **Element Plus** + **Pinia** + **Vue Router** + **Axios**  
- 构建产物：`frontend-admin/dist/`，可由 Nginx 静态托管或由 Django `collectstatic` 策略外置。

---

## 11.2 本地开发

```bash
cd frontend-admin
npm install
npm run dev
```

默认 Vite 开发服务器端口 **`5173`**（以 `vite.config` 为准）。

---

## 11.3 与 Django 联调

### 11.3.1 代理

`vite.config` 中通常配置：

- `/ip-guard` → Django 后端（如 `http://127.0.0.1:8010`）  
- `/admin` → 可选，便于同窗口打开 Django Admin

这样前端代码里 Axios `baseURL` 可写 **`/ip-guard/api`**，由代理转发。

### 11.3.2 鉴权模式

登录页支持：

- **Session**：`loginApi` → Cookie 会话；Axios `withCredentials: true`。  
- **JWT**：`jwtLoginApi` → 本地存 `access_token` / `refresh_token`；请求拦截器加 `Authorization: Bearer`。

遇 **401** 时，使用**无拦截器的 raw 客户端**调用 `jwtRefreshApi`，成功后重试原请求一次，避免死循环（见 `src/api/http.js`）。

### 11.3.3 CSRF

统一实例启用 `xsrfCookieName: csrftoken`、`xsrfHeaderName: X-CSRFToken`。登录前调用 `getCsrf()`。

---

## 11.4 页面功能说明

| 路由 | 功能 | 依赖权限（典型） |
|------|------|------------------|
| `/login` | 登录（Session/JWT 切换） | 无 |
| `/dashboard` | 运营大盘：统计卡片、世界地图热力图、国家柱状图、近期记录（所有元素可点击跳转审计日志） | `view_ipaccesslog` |
| `/policy` | 策略编辑、地理池状态、同步按钮 | 查看/修改策略权限 |
| `/ban` | 封禁列表与操作 | `view_ipbanrecord` / `change_ipbanrecord` |
| `/logs` | 审计分页与 CSV 导出（支持从 Dashboard 跳转自动填充筛选条件） | `view_ipaccesslog` |
| `/health` | Redis 延迟、熔断、地理池摘要 | `view_ipguardpolicy` |

菜单与路由通过 `authStore.hasPerm` 控制；无权限路由会被重定向到首个可访问页。

---

## 11.5 生产构建

```bash
cd frontend-admin
npm run build
```

将 `dist/` 部署到 CDN 或反代静态目录；**务必**配置与开发环境一致的 **API 反向代理**到 Django 的 `/ip-guard/` 前缀。

---

## 11.6 与 Django 同域部署建议

- 推荐 **同域**（如 `https://ops.example.com/ip-guard/` 与 `https://ops.example.com/static-admin/`），减少 CORS 与第三方 Cookie 限制。  
- 若跨域：需配置 `CORS_ALLOWED_ORIGINS`、Cookie `SameSite`、CSRF `CSRF_TRUSTED_ORIGINS` 等，复杂度显著上升。

---

## 11.7 常见问题

| 问题 | 处理 |
|------|------|
| POST 403 CSRF | 确认已 GET csrf、Cookie 域一致、反代未剥头；Vite 代理需配置 `cookieDomainRewrite: { "*": "" }`；Django 需配置 `CSRF_TRUSTED_ORIGINS` 含前端地址 |
| JWT 下策略保存 403 | 用户缺少 `change_ipguardpolicy` |
| 导出 CSV 空/401 | JWT 模式下导出使用独立 axios，需带 Bearer |
| 地图不显示 | 检查 `country_distribution` 数据与国家 GeoJSON 字段对齐 |
| Dashboard 点击无跳转 | 确认路由 `/logs` 存在且用户有 `view_ipaccesslog` 权限 |

---

## 11.8 相关文档

- API：[09-管理REST-API参考](./09-管理REST-API参考.md)  
- 认证：[10-认证CSRF-JWT与权限模型](./10-认证CSRF-JWT与权限模型.md)  
- 运维部署：[13-运维部署与监控](./13-运维部署与监控.md)
