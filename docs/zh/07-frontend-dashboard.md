# 前端仪表盘使用指南

## 概述

Django IP Safeguard 包含一个基于 Vue.js 的管理仪表盘，入口为 **`/ip-guard/`**（与 `path('ip-guard/', include(...))` 对应）。

## 浏览器标签图标（Logo）

入口页 `contrib/admin_frontend/index.html` 的 `<head>` 中已配置 **`rel="icon"`**（SVG）与 **`apple-touch-icon`**，构建后地址为 **`/ip-guard/logo.svg`**（源文件位于 `contrib/admin_frontend/public/logo.svg`，与侧栏/登录页所用图形一致）。

## 功能

### 仪表盘

主仪表盘提供：
- **统计卡片**：已封禁 IP 总数、访问次数、今日阻止数
- **实时图表**：访问模式、阻止 IP 分布
- **最近记录**：带有决策状态的最新访问日志
- **世界地图**：访问尝试的地理分布

### 策略管理

配置 IP 封禁规则：
- **IP 白名单/黑名单**：添加单个 IP 或 CIDR 范围
- **国家多选**：国家白/黑名单支持可搜索的多选下拉（国家名 + ISO2 代码）
- **限流**：配置每分钟请求限制
- **GeoIP 规则**：按国家封禁/允许
- **自动封禁**：设置自动阻止阈值

### 访问日志

查看和搜索访问历史：
- 按 IP、决策、日期范围筛选
- 导出日志到 CSV
- 查看详细访问信息

### 封禁管理

管理已封禁 IP：
- 查看所有带过期时间的已封禁 IP
- 手动封禁/解封
- 设置封禁时长和原因

### 用户设置

- **API 密钥**：创建、列出和撤销 API 密钥
- **2FA 设置**：启用双因素认证
- **个人资料**：更新邮箱、修改密码

### 系统用户管理（Django 账号）

Vue 控制台中的「**用户设置**」仅管理**当前登录用户**本人（资料、密码、2FA、API 密钥等）。对 **其他 Django 系统用户**（新建账号、分配组、Staff/Superuser、启用/停用、重置密码等），请在侧栏「**系统用户管理**」中完成：列表分页查询，**新建用户**/**编辑**在页面内对话框操作，无需跳转 Django Admin。

需已为账号分配 `auth` 应用下相应权限（如 `auth.view_user`、`auth.add_user`、`auth.change_user`）；超级用户拥有全部权限。插件页面调用 `GET/POST /ip-guard/api/admin/users/` 与 `PATCH /ip-guard/api/admin/users/<id>/`（与 Django `auth` 权限一致）。若仍需使用原生 Django Admin，可自行访问 **`/admin/auth/user/`**。

### 系统设置

配置系统选项：
- 缓存设置
- 威胁情报提供者
- 日志偏好

## 登录

1. 访问 `/ip-guard/`（或带 Vue 子路径，如 `/ip-guard/login`）
2. 输入用户名和密码
3. 如果启用，完成 2FA 验证
4. 进入仪表盘

## 导航

- **侧边栏**：主导航菜单
- **头部**：搜索、通知、用户菜单
- **面包屑**：当前在应用中的位置

## 暗黑模式

使用头部的切换按钮可以开启暗黑模式。

## 语言

使用语言选择器可以在英语和中文之间切换。

## 键盘快捷键

| 快捷键 | 操作 |
|--------|------|
| `Ctrl+K` | 打开命令面板 |
| `Esc` | 关闭弹窗/对话框 |
| `Enter` | 确认操作 |

## 常见问题

- **打开 `/ip-guard/` 却触发下载 `index.html`**：说明响应头里 `Content-Type` 不是 `text/html`（旧版本对 `.html` 误用了 `application/octet-stream`）。请使用当前包版本；入口页必须由服务端声明 `text/html` 浏览器才会渲染 Vue 应用。
- **页面空白、仅见 `#app` 空壳**：请确认前端构建的 `vite.config.js` 中 `base` 为 `/ip-guard/`，且路由使用 `createWebHistory(import.meta.env.BASE_URL)`，与 Django 挂载路径一致。

## 移动端支持

仪表盘是响应式的，可以在移动设备上使用。但是为了获得最佳体验，建议使用桌面浏览器。
