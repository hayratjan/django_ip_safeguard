# Frontend Dashboard Guide

## Overview

Django IP Safeguard includes a Vue.js-based admin dashboard accessible at `/ip-guard/admin-frontend/`.

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

### System Settings

Configure system options:
- Cache settings
- Threat intelligence providers
- Logging preferences

## Login

1. Visit `/ip-guard/admin-frontend/`
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

## Mobile Support

The dashboard is responsive and works on mobile devices. However, for the best experience, use a desktop browser.
