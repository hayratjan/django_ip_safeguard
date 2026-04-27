# Database Models

## Overview

Django IP Safeguard provides several models for managing IP policies, access logs, and authentication.

## Model Overview

| Model | Description |
|-------|-------------|
| `IpGuardPolicy` | Main policy configuration |
| `IpAccessLog` | Access log records |
| `ApiKey` | API key storage |
| `ApiKeyUsageLog` | API key usage logs |
| `ScheduledTask` | Scheduled task definitions |
| `TaskExecutionLog` | Task execution history |
| `UserProfile` | Extended user profile |

## IpGuardPolicy

The main policy model for configuring IP guard rules.

```python
class IpGuardPolicy(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # IP Rules
    ip_whitelist = models.TextField(blank=True)  # JSON list
    ip_blacklist = models.TextField(blank=True)  # JSON list

    # Rate Limiting
    rate_limit_enabled = models.BooleanField(default=False)
    rate_limit_requests = models.IntegerField(default=60)
    rate_limit_window = models.IntegerField(default=60)  # seconds

    # GeoIP Rules
    geoip_enabled = models.BooleanField(default=False)
    allowed_countries = models.TextField(blank=True)  # JSON list
    blocked_countries = models.TextField(blank=True)  # JSON list

    # Auto Ban
    auto_ban_enabled = models.BooleanField(default=False)
    auto_ban_threshold = models.IntegerField(default=5)
    auto_ban_duration = models.IntegerField(default=30)  # minutes

    # Policy Settings
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### Usage

```python
from django_ip_safeguard.models import IpGuardPolicy

# Create policy
policy = IpGuardPolicy.objects.create(
    name="Block China",
    geoip_enabled=True,
    blocked_countries='["CN"]'
)

# Get active policy
policy = IpGuardPolicy.objects.filter(is_active=True).first()
```

## IpAccessLog

Records all access attempts.

```python
class IpAccessLog(models.Model):
    ip_address = models.GenericIPAddressField()
    path = models.CharField(max_length=500)
    method = models.CharField(max_length=10)

    # Request Info
    user_agent = models.TextField(blank=True)
    referer = models.TextField(blank=True)

    # Response Info
    status_code = models.IntegerField()
    decision = models.CharField(max_length=20)  # allow, block, challenge, rate_limit

    # Risk Assessment
    risk_score = models.FloatField(null=True, blank=True)
    risk_level = models.CharField(max_length=20, blank=True)

    # GeoIP Info
    country = models.CharField(max_length=2, blank=True)
    city = models.CharField(max_length=100, blank=True)
    isp = models.CharField(max_length=200, blank=True)

    # Timing
    response_time = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
```

### Usage

```python
from django_ip_safeguard.models import IpAccessLog

# Query recent blocked IPs
blocked = IpAccessLog.objects.filter(
    decision="block",
    created_at__gte=timezone.now() - timezone.timedelta(hours=1)
).values("ip_address").annotate(count=Count("id"))

# Search logs
logs = IpAccessLog.objects.filter(
    ip_address__startswith="192.168."
).order_by("-created_at")[:100]
```

## ApiKey

Stores API keys for programmatic access.

```python
class ApiKey(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    # Key Data
    key_id = models.CharField(max_length=32, unique=True)
    key_hash = models.CharField(max_length=64)

    # Usage Limits
    rate_limit = models.IntegerField(default=100)
    daily_limit = models.IntegerField(null=True, blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
```

### Usage

```python
from django_ip_safeguard.models import ApiKey

# Create API key
api_key = ApiKey.create_key(user=request.user, name="My App")

# Use API key
response = requests.get(
    "https://example.com/ip-guard/api/dashboard/",
    headers={"X-API-Key": api_key.key}
)

# Revoke key
api_key.delete()
```

## ApiKeyUsageLog

Tracks API key usage.

```python
class ApiKeyUsageLog(models.Model):
    api_key = models.ForeignKey(ApiKey, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField()
    endpoint = models.CharField(max_length=200)
    method = models.CharField(max_length=10)
    status_code = models.IntegerField()
    response_time = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
```

## ScheduledTask

Defines scheduled tasks for background processing.

```python
class ScheduledTask(models.Model):
    TASK_TYPES = [
        ("sync_geo_ip", "Sync GeoIP Pools"),
        ("sync_threat_intel", "Sync Threat Intel"),
        ("snapshot_reputation", "Snapshot IP Reputation"),
        ("cleanup_logs", "Cleanup Old Logs"),
        ("custom", "Custom Command"),
    ]

    name = models.CharField(max_length=100)
    task_type = models.CharField(max_length=50, choices=TASK_TYPES)

    # Schedule
    cron_expression = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    # Task Config
    command = models.CharField(max_length=500, blank=True)
    arguments = models.TextField(blank=True)

    # Status
    last_run_at = models.DateTimeField(null=True, blank=True)
    last_status = models.CharField(max_length=20, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### Usage

```python
from django_ip_safeguard.models import ScheduledTask

# Create scheduled task
task = ScheduledTask.objects.create(
    name="Daily GeoIP Sync",
    task_type="sync_geo_ip",
    cron_expression="0 2 * * *",  # 2 AM daily
)
```

## TaskExecutionLog

Records task execution history.

```python
class TaskExecutionLog(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("timeout", "Timeout"),
    ]

    task = models.ForeignKey(ScheduledTask, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    output = models.TextField(blank=True)
    error = models.TextField(blank=True)

    duration = models.FloatField(null=True, blank=True)  # seconds
```

## UserProfile

Extended user profile with 2FA support.

```python
class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    # 2FA Settings
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=32, blank=True)
    two_factor_methods = models.JSONField(default=list)

    # Security
    login_history = models.JSONField(default=list)
    blocked_until = models.DateTimeField(null=True, blank=True)

    # Preferences
    language = models.CharField(max_length=10, default="en")
    theme = models.CharField(max_length=20, default="light")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

## Admin Interface

All models are registered with Django admin for easy management:

```python
# admin.py
from django_ip_safeguard.admin import (
    IpGuardPolicyAdmin,
    IpAccessLogAdmin,
    ApiKeyAdmin,
    ScheduledTaskAdmin,
)

admin.site.register(IpGuardPolicy, IpGuardPolicyAdmin)
admin.site.register(IpAccessLog, IpAccessLogAdmin)
admin.site.register(ApiKey, ApiKeyAdmin)
admin.site.register(ScheduledTask, ScheduledTaskAdmin)
```
