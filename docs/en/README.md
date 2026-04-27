# Django IP Safeguard

![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)
![Django](https://img.shields.io/badge/Django-6.0-green.svg)
![Python](https://img.shields.io/badge/Python-3.10+-yellow.svg)
![License](https://img.shields.io/badge/License-MIT-orange.svg)

A comprehensive Django IP risk management plugin providing IP risk querying, geographical rules, and automatic blocking capabilities.

## Features

- **IP Risk Assessment**: Query multiple threat intelligence sources for IP reputation
- **Geographic Blocking**: Block or allow IPs based on country/region rules
- **Rate Limiting**: Protect against brute force and DDoS attacks
- **Auto Ban System**: Automatically block malicious IPs based on configurable rules
- **Real-time Dashboard**: Monitor access logs, blocked IPs, and security events
- **Multi-factor Authentication**: Support for 2FA and API key authentication
- **Celery Integration**: Asynchronous task scheduling for heavy operations
- **Redis Caching**: Efficient caching with circuit breaker pattern
- **i18n Support**: English and Chinese language support

## Requirements

- Python 3.10+
- Django 6.0+
- Redis 5.0+
- Node.js 18+ (for frontend development)

## Installation

### From PyPI (Recommended)

```bash
pip install django-ip-safeguard
```

### From Source

```bash
git clone https://github.com/hayratjan/django_ip_safeguard.git
cd django_ip_safeguard
pip install -e .
```

### Development Installation

```bash
pip install -e ".[dev,geoip2]"
```

## Quick Start

### 1. Add to Django Settings

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "django_ip_safeguard",
    "django.contrib.admin",
    # ...
]

MIDDLEWARE = [
    # ...
    "django_ip_safeguard.middleware.IpGuardMiddleware",
    # ...
]

# Required: Add IP Guard URLs
ROOT_URLCONF = "your_project.urls"

# Optional: Use Redis for caching (recommended)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
    }
}
```

### 2. Update URLs

```python
# urls.py
from django.urls import path, include

urlpatterns = [
    # ...
    path("ip-guard/", include("django_ip_safeguard.urls")),
    # ...
]
```

### 3. Run Migrations

```bash
python manage.py migrate
```

### 4. Create Admin User

```bash
python manage.py createsuperuser
```

### 5. Build Frontend (Optional)

```bash
python manage.py build_frontend
```

### 6. Run Development Server

```bash
python manage.py runserver 8000
```

Visit `http://localhost:8000/ip-guard/` for the admin dashboard.

## Configuration

### Essential Settings

```python
# settings.py

IP_GUARD = {
    # Enable/disable the middleware
    "ENABLED": True,

    # IPs that bypass all checks (whitelist)
    "WHITELIST_IPS": ["127.0.0.1", "10.0.0.0/8"],

    # IPs that are always blocked (blacklist)
    "BLACKLIST_IPS": [],

    # Default policy when no rules match
    "DEFAULT_POLICY": "allow",  # or "deny"

    # Enable 2FA for admin users
    "ENABLE_2FA": True,

    # JWT settings
    "JWT": {
        "SECRET_KEY": "your-secret-key-change-in-production",
        "ACCESS_TOKEN_LIFETIME_MINUTES": 60,
        "REFRESH_TOKEN_LIFETIME_DAYS": 7,
    },

    # Redis cache settings
    "CACHE": {
        "ENABLED": True,
        "BACKEND": "redis",
        "LOCATION": "redis://127.0.0.1:6379/1",
    },

    # Rate limiting
    "RATE_LIMIT": {
        "ENABLED": True,
        "REQUESTS_PER_MINUTE": 60,
    },

    # Auto-ban settings
    "AUTO_BAN": {
        "ENABLED": True,
        "THRESHOLD": 5,  # Block after 5 failed attempts
        "DURATION_MINUTES": 30,
    },
}
```

### Complete Settings Reference

See [docs/en/04-configuration-reference.md](docs/en/04-configuration-reference.md) for the full list of configuration options.

## Project Structure

```
django_ip_safeguard/
├── __init__.py           # Package initialization
├── admin.py              # Django admin configuration
├── apps.py               # App configuration
├── celery.py             # Celery configuration
├── conf.py               # Settings management
├── exceptions.py         # Custom exceptions
├── middleware.py         # IP guard middleware
├── models.py             # Database models
├── signals.py            # Django signals
├── urls.py               # URL routing
├── views.py              # API views
├── types.py              # Type definitions
├── services/             # Business logic services
│   ├── audit_service.py
│   ├── ban_service.py
│   ├── cache.py
│   ├── jwt_service.py
│   ├── policy_service.py
│   ├── risk_engine.py
│   └── ...
├── migrations/           # Database migrations
├── management/           # Custom management commands
│   └── commands/
├── locale/               # Translation files
└── contrib/
    └── admin_frontend/   # Vue.js admin dashboard
        ├── src/          # Frontend source code
        ├── static/       # Built static files
        └── management/   # Frontend build commands
```

## Management Commands

```bash
# Build frontend assets
python manage.py build_frontend

# Sync GeoIP pools
python manage.py sync_geo_ip_pools

# Update GeoIP database
python manage.py update_geoip2_db

# Sync threat intelligence
python manage.py sync_threat_intel

# Run task scheduler
python manage.py run_task_scheduler

# Snapshot IP reputation
python manage.py snapshot_ip_reputation
```

## API Reference

### Authentication

- `POST /ip-guard/api/auth/login/` - User login
- `POST /ip-guard/api/auth/jwt/login/` - JWT login
- `POST /ip-guard/api/auth/jwt/refresh/` - Refresh JWT token
- `POST /ip-guard/api/auth/logout/` - User logout
- `GET /ip-guard/api/auth/me/` - Get current user

### API Keys

- `POST /ip-guard/api/auth/api-key/login/` - Login with API key
- `GET /ip-guard/api/auth/api-key/list/` - List API keys
- `POST /ip-guard/api/auth/api-key/create/` - Create API key
- `POST /ip-guard/api/auth/api-key/revoke/` - Revoke API key
- `GET /ip-guard/api/auth/api-key/logs/` - Get API key usage logs

### Dashboard

- `GET /ip-guard/api/dashboard/` - Dashboard statistics
- `GET /ip-guard/api/recent-records/` - Recent access records
- `GET /ip-guard/api/user-stats-chart/` - User statistics chart

### Policy & Access Control

- `GET /ip-guard/api/policy/` - Get current policy
- `POST /ip-guard/api/ban/` - Ban an IP
- `POST /ip-guard/api/unban/` - Unban an IP
- `GET /ip-guard/api/ban-list/` - List banned IPs
- `GET /ip-guard/api/access-logs/` - Access logs

### Admin

- `GET /ip-guard/api/health/` - Health check
- `GET /ip-guard/api/system-settings/` - System settings
- `GET /ip-guard/api/security-audit-logs/` - Security audit logs
- `GET /ip-guard/api/scheduled-tasks/` - Scheduled tasks

## Frontend Dashboard

The package includes a Vue.js-based admin dashboard with:

- **Dashboard**: Real-time statistics and charts
- **Policy Management**: Configure IP blocking rules
- **Access Logs**: View and search access history
- **Ban Management**: View and manage banned IPs
- **User Settings**: API key management, 2FA setup
- **System Settings**: Configure system options

Access the dashboard at `/ip-guard/`

## Database Models

- `IpGuardPolicy`: Main policy configuration
- `IpAccessLog`: Access log records
- `ApiKey`: API key storage
- `ApiKeyUsageLog`: API key usage logs
- `ScheduledTask`: Scheduled task definitions
- `TaskExecutionLog`: Task execution history
- `UserProfile`: Extended user profile with 2FA

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/hayratjan/django_ip_safeguard.git
cd django_ip_safeguard

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e ".[dev,geoip2]"

# Run tests
pytest

# Run development server
cd demo_project
python manage.py runserver
```

### Running Tests

```bash
pytest tests/ -v
```

## Documentation

Full documentation is available in the `docs/` directory:

- [Quick Start Guide](docs/en/01-quick-start.md)
- [Installation & Requirements](docs/en/02-installation.md)
- [Middleware & Request Flow](docs/en/03-middleware.md)
- [Configuration Reference](docs/en/04-configuration-reference.md)
- [Database Models](docs/en/05-models.md)
- [API Reference](docs/en/06-api-reference.md)
- [Frontend Dashboard](docs/en/07-frontend-dashboard.md)
- [Deployment Guide](docs/en/08-deployment.md)
- [Development Guide](docs/en/09-development.md)

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

- **Issues**: https://github.com/hayratjan/django_ip_safeguard/issues
- **Documentation**: https://github.com/hayratjan/django_ip_safeguard#readme
