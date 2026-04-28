# Development Guide

## Setup Development Environment

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL or MySQL (optional)
- Redis (optional)

### 1. Clone Repository

```bash
git clone https://github.com/hayratjan/django_ip_safeguard.git
cd django_ip_safeguard
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows
```

### 3. Install Dependencies

```bash
# Install package in development mode with all dependencies
pip install -e ".[dev,geoip2]"

# Install frontend dependencies
cd django_ip_safeguard/contrib/admin_frontend
npm install
cd ../../..
```

### 4. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=django_ip_safeguard --cov-report=html

# Run specific test
pytest tests/test_middleware.py -v
```

### 5. Run Development Server

```bash
# From the demo project
cd demo_project
python manage.py runserver 8000
```

### 6. Verify pip install with **demo2** (optional)

Build the wheel from the repository root:

```bash
python -m build   # produces dist/django_ip_safeguard-<version>-py3-none-any.whl
```

Use the **demo2** sample so dependencies come only from the wheel (similar to PyPI):

```bash
cd demo2
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install ../dist/django_ip_safeguard-0.2.1-py3-none-any.whl
# or pip install -r requirements-from-dist.txt (adjust wheel version/path if needed)
python manage.py migrate
python manage.py check
python manage.py runserver 8000
```

In `demo2/demo2/settings.py`, `LOCALE_PATHS` points at the installed package’s `locale` directory (no hard-coded path to a source checkout).

## Project Structure

```
django_ip_safeguard/
├── __init__.py              # Package init, app config
├── admin.py                 # Django admin registration
├── apps.py                  # App configuration
├── celery.py                # Celery configuration
├── conf.py                  # Settings management
├── exceptions.py            # Custom exceptions
├── middleware.py            # IP Guard middleware
├── models.py                # Database models
├── signals.py               # Django signals
├── urls.py                  # URL routing
├── views.py                 # API views
├── types.py                 # Type definitions
├── services/                # Business logic
│   ├── audit_service.py     # Audit logging
│   ├── ban_service.py       # IP banning
│   ├── cache.py             # Caching
│   ├── jwt_service.py       # JWT handling
│   ├── policy_service.py    # Policy management
│   ├── risk_engine.py       # Risk assessment
│   ├── provider_*.py        # Various providers
│   └── ...
├── migrations/              # Database migrations
├── management/              # Custom commands
│   └── commands/
├── locale/                  # Translation files
│   ├── en/
│   └── zh_Hans/
└── contrib/
    └── admin_frontend/      # Vue.js dashboard
        ├── src/             # Frontend source
        ├── static/          # Built assets
        └── management/      # Build commands
```

## Adding New Features

### 1. Add New Model

```python
# models.py
class MyFeature(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
```

### 2. Register with Admin

```python
# admin.py
@admin.register(MyFeature)
class MyFeatureAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name"]
```

### 3. Create API View

```python
# views.py
from django.http import JsonResponse
from django.views import View

class MyFeatureListView(View):
    def get(self, request):
        features = MyFeature.objects.filter(is_active=True)
        data = [{"id": f.id, "name": f.name} for f in features]
        return JsonResponse({"items": data})
```

### 4. Add URL Route

```python
# urls.py
path("my-features/", MyFeatureListView.as_view(), name="my_feature_list"),
```

## Frontend Development

### Setup

```bash
cd django_ip_safeguard/contrib/admin_frontend
npm install
```

### Development Mode

```bash
npm run dev
```

The dev server runs on port 5173 with proxy to Django backend.

### Build for Production

```bash
npm run build
```

Or use Django management command:

```bash
python manage.py build_frontend
```

## Code Style

### Python

- Follow PEP 8
- Use type hints where possible
- Use `from django_ip_safeguard import ...` for imports

### JavaScript/Vue

- Use Vue 3 Composition API
- Use `<script setup>` syntax
- Follow ESLint rules

## Testing

### Write Tests

```python
# tests/test_my_feature.py
import pytest
from django_ip_safeguard.models import MyFeature

@pytest.mark.django_db
def test_my_feature_creation():
    feature = MyFeature.objects.create(name="Test")
    assert feature.name == "Test"
    assert feature.is_active is True
```

### Run Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=django_ip_safeguard --cov-report=term-missing

# Specific file
pytest tests/test_middleware.py -v

# Watch mode
ptw  # pytest-watch
```

## Internationalization

### Add Translation String

```python
# Python
from django.utils.translation import gettext_lazy as _

name = _("Feature Name")
```

```html
<!-- Template -->
<h1>{% trans "Welcome" %}</h1>
```

```javascript
// JavaScript
const message = t("welcome_message");
```

### Update Translation Files

```bash
# Extract strings
python manage.py makemessages -l zh_Hans

# Compile messages
python manage.py compilemessages
```

## Debugging

### Django Debug Toolbar

Install and configure django-debug-toolbar for local development.

### Logging

```python
import logging

logger = logging.getLogger(__name__)

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

### IPython Debugging

```python
from IPython import embed; embed()
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests
5. Submit a pull request

## Code Review Checklist

- [ ] Code follows project style
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No breaking changes
- [ ] All tests pass
- [ ] Type hints added (Python)
