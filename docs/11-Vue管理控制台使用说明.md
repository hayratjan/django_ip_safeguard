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
| `/user-chart` | 用户图表：每日趋势、风险分布、小时分布、国家 Top10 | `view_ipaccesslog` |
| `/user-settings` | 用户设置：修改密码、修改邮箱、2FA 双因素认证 | 无（登录即可访问） |
| `/system-settings` | 系统设置：语言、主题、安全策略、地理池 | `view_ipguardpolicy` |

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

## 11.8 主题与外观

### 11.8.1 主题模式

支持三种主题模式，通过顶部导航栏的主题下拉菜单切换：

- **亮色**：默认浅色主题
- **暗色**：深色主题，适合低光环境
- **跟随系统**：自动跟随操作系统暗色/亮色设置

主题偏好保存在 `localStorage`（key: `ip_guard_theme`），刷新后自动恢复。

### 11.8.2 主题颜色

系统设置 → 通用 页面提供 **8 种主题色** 可选：默认蓝、靛蓝、紫色、翡翠绿、琥珀、红色、粉色、青色。选择后全局 Element Plus 主色及渐变色自动更新，偏好保存在 `localStorage`（key: `ip_guard_color`）。

---

## 11.9 用户设置

路由：`/user-settings`，无需特殊权限，所有登录用户可访问。

### 11.9.1 个人信息

显示当前用户名、邮箱、角色（Superuser/Staff/User）、2FA 状态、注册时间、最后登录时间。

### 11.9.2 修改密码

- 需输入旧密码、新密码（最少 8 位）、确认新密码
- 后端 API：`POST /api/auth/change-password/`
- 修改成功后需重新登录

### 11.9.3 修改邮箱

- 输入新邮箱地址，后端验证格式
- 后端 API：`POST /api/auth/change-email/`

### 11.9.4 双因素认证 (2FA)

基于 TOTP（Time-based One-Time Password）标准，兼容 Google Authenticator、Microsoft Authenticator 等应用。

**启用流程**：
1. 点击「启用 2FA」按钮，后端生成密钥和 `provisioning_uri`
2. 前端使用 `qrcode` 库生成二维码，用户用认证器 App 扫码
3. 输入认证器显示的 6 位验证码，后端验证后启用 2FA

**禁用流程**：
1. 输入当前认证器显示的 6 位验证码
2. 后端验证后清除密钥并禁用 2FA

> **注意**：2FA 功能依赖 `pyotp` Python 包，未安装时后端返回错误提示。

**后端 API**：
- `GET /api/auth/2fa/status/` — 查询 2FA 状态
- `POST /api/auth/2fa/setup/` — 生成密钥和 URI
- `POST /api/auth/2fa/verify/` — 验证并启用
- `POST /api/auth/2fa/disable/` — 验证并禁用

---

## 11.10 系统设置

路由：`/system-settings`，需要 `view_ipguardpolicy` 权限。

### 11.10.1 通用设置

- **默认语言**：切换系统界面语言（中文/English），同时同步到后端
- **主题模式**：亮色/暗色/跟随系统
- **主题颜色**：8 种预设主色可选

### 11.10.2 安全设置

需要策略修改权限才能编辑，包含：
- 风险阈值（0-100）
- 每分钟请求上限
- 拦截状态码（400-499）
- 全局失败放行开关
- 数据库审计日志开关
- 情报缓存 TTL
- 封禁 TTL

### 11.10.3 地理池设置

- 中国内网段池规则（关闭/仅允许池内/池内拦截）
- 国际网段池规则（关闭/仅允许池内/池内拦截）

**后端 API**：`GET/POST /api/system-settings/`

---

## 11.11 用户图表

路由：`/user-chart`，需要 `view_ipaccesslog` 权限。

提供 4 类可视化图表，支持 3/7/14/30 天范围选择：

| 图表 | 说明 |
|------|------|
| 每日趋势 | 按日堆叠柱状图，展示放行/拦截数量 |
| 风险分布 | 环形图，展示高/中/低风险占比 |
| 小时分布 | 折线图，展示 24 小时请求和拦截模式 |
| 国家 Top10 | 横向柱状图，展示访问量 Top10 国家 |

图表使用 ECharts + vue-echarts 渲染，支持暗色主题自适应。

**后端 API**：`GET /api/user-stats-chart/?days=N`

---

## 11.12 相关文档

- API：[09-管理REST-API参考](./09-管理REST-API参考.md)  
- 认证：[10-认证CSRF-JWT与权限模型](./10-认证CSRF-JWT与权限模型.md)  
- 运维部署：[13-运维部署与监控](./13-运维部署与监控.md)
