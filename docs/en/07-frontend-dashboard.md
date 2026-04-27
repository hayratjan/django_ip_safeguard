# Frontend Dashboard Guide

## Overview

Django IP Safeguard includes a Vue.js-based admin dashboard served at **`/ip-guard/`** (under `path('ip-guard/', include(...))`).

## Features

### Dashboard

The main dashboard provides:
- **Statistics Cards**: Total banned IPs, access count, blocked today
- **Real-time Charts**: Access patterns, blocked IP distribution
- **Recent Records**: Latest access logs with decision status
- **World Map**: Geographic distribution of access attempts

### Policy Management

Configure IP blocking rules:
- **IP Whitelist/Blacklist**: Add individual IPs or CIDR ranges
- **Rate Limiting**: Configure requests per minute limits
- **GeoIP Rules**: Block/allow by country
- **Auto Ban**: Set thresholds for automatic blocking

### Access Logs

View and search access history:
- Filter by IP, decision, date range
- Export logs to CSV
- View detailed access information

### Ban Management

Manage banned IPs:
- View all banned IPs with expiration
- Manual ban/unban
- Set ban duration and reason

### User Settings

- **API Keys**: Create, list, and revoke API keys
- **2FA Setup**: Enable two-factor authentication
- **Profile**: Update email, change password

### Django system users (accounts)

**User Settings** in the Vue console applies only to the **signed-in user** (profile, password, 2FA, API keys). To manage **other Django users** (create/edit accounts, groups, staff/superuser flags), use one of the following:

1. **Django Admin (recommended)**  
   Open **`/admin/auth/user/`** (or **`/admin/`** then Users). Requires the appropriate `auth` permissions (e.g. `auth.view_user`, `auth.add_user`, `auth.change_user`); superusers have full access.

2. **In-console entry**  
   If the account is a superuser or has `auth.view_user`, the sidebar shows **System user management** for paginated list/edit inside Vue, with an optional jump to Admin for advanced operations.

3. **Built-in API**  
   The package exposes `GET/POST /ip-guard/api/admin/users/` and `PATCH /ip-guard/api/admin/users/<id>/`, aligned with Django `auth` permissions, used by the system user management page.

### System Settings

Configure system options:
- Cache settings
- Threat intelligence providers
- Logging preferences

## Login

1. Visit `/ip-guard/` (or a client route such as `/ip-guard/login`)
2. Enter username and password
3. Complete 2FA verification if enabled
4. Access dashboard

## Navigation

- **Sidebar**: Main navigation menu
- **Header**: Search, notifications, user menu
- **Breadcrumbs**: Current location in the app

## Dark Mode

Toggle dark mode using the theme switcher in the header.

## Language

Switch between English and Chinese using the language selector.

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+K` | Open command palette |
| `Esc` | Close modal/dialog |
| `Enter` | Confirm action |

## Troubleshooting

- **Visiting `/ip-guard/` downloads `index.html` instead of showing the app**: The response used the wrong `Content-Type` (e.g. `application/octet-stream` instead of `text/html`). Upgrade to a build that maps `.html` correctly; the browser only renders the SPA when the entry document is served as HTML.
- **Blank page with an empty `#app` shell**: Ensure the Vite `base` is `/ip-guard/` and the router uses `createWebHistory(import.meta.env.BASE_URL)` so client assets and routes match the Django mount path.

## Mobile Support

The dashboard is responsive and works on mobile devices. However, for the best experience, use a desktop browser.
