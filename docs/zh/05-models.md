# 数据库模型

## 概述

Django IP Safeguard 提供多个模型来管理 IP 策略、访问日志和认证。

## 模型概览

| 模型 | 描述 |
|------|------|
| `IpGuardPolicy` | 主要策略配置 |
| `IpAccessLog` | 访问日志记录 |
| `ApiKey` | API 密钥存储 |
| `ApiKeyUsageLog` | API 密钥使用日志 |
| `ScheduledTask` | 计划任务定义 |
| `TaskExecutionLog` | 任务执行历史 |
| `UserProfile` | 扩展用户资料 |

## IpGuardPolicy

主要策略模型，用于配置 IP 防护规则。

```python
class IpGuardPolicy(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # IP 规则
    ip_whitelist = models.TextField(blank=True)  # JSON 列表
    ip_blacklist = models.TextField(blank=True)  # JSON 列表

    # 限流
    rate_limit_enabled = models.BooleanField(default=False)
    rate_limit_requests = models.IntegerField(default=60)
    rate_limit_window = models.IntegerField(default=60)  # 秒

    # GeoIP 规则
    geoip_enabled = models.BooleanField(default=False)
    allowed_countries = models.TextField(blank=True)  # JSON 列表
    blocked_countries = models.TextField(blank=True)  # JSON 列表

    # 自动封禁
    auto_ban_enabled = models.BooleanField(default=False)
    auto_ban_threshold = models.IntegerField(default=5)
    auto_ban_duration = models.IntegerField(default=30)  # 分钟

    # 策略设置
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### 使用示例

```python
from django_ip_safeguard.models import IpGuardPolicy

# 创建策略
policy = IpGuardPolicy.objects.create(
    name="Block China",
    geoip_enabled=True,
    blocked_countries='["CN"]'
)

# 获取活跃策略
policy = IpGuardPolicy.objects.filter(is_active=True).first()
```

## IpAccessLog

记录所有访问尝试。

```python
class IpAccessLog(models.Model):
    ip_address = models.GenericIPAddressField()
    path = models.CharField(max_length=500)
    method = models.CharField(max_length=10)

    # 请求信息
    user_agent = models.TextField(blank=True)
    referer = models.TextField(blank=True)

    # 响应信息
    status_code = models.IntegerField()
    decision = models.CharField(max_length=20)  # allow, block, challenge, rate_limit

    # 风险评估
    risk_score = models.FloatField(null=True, blank=True)
    risk_level = models.CharField(max_length=20, blank=True)

    # GeoIP 信息
    country = models.CharField(max_length=2, blank=True)
    city = models.CharField(max_length=100, blank=True)
    isp = models.CharField(max_length=200, blank=True)

    # 时间
    response_time = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
```

### 使用示例

```python
from django_ip_safeguard.models import IpAccessLog

# 查询最近被阻止的 IP
blocked = IpAccessLog.objects.filter(
    decision="block",
    created_at__gte=timezone.now() - timezone.timedelta(hours=1)
).values("ip_address").annotate(count=Count("id"))

# 搜索日志
logs = IpAccessLog.objects.filter(
    ip_address__startswith="192.168."
).order_by("-created_at")[:100]
```

## ApiKey

存储 API 密钥以供程序化访问。

```python
class ApiKey(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    # 密钥数据
    key_id = models.CharField(max_length=32, unique=True)
    key_hash = models.CharField(max_length=64)

    # 使用限制
    rate_limit = models.IntegerField(default=100)
    daily_limit = models.IntegerField(null=True, blank=True)

    # 状态
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
```

### 使用示例

```python
from django_ip_safeguard.models import ApiKey

# 创建 API 密钥
api_key = ApiKey.create_key(user=request.user, name="My App")

# 使用 API 密钥
response = requests.get(
    "https://example.com/ip-guard/api/dashboard/",
    headers={"X-API-Key": api_key.key}
)

# 撤销密钥
api_key.delete()
```

## ApiKeyUsageLog

追踪 API 密钥使用情况。

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

定义后台处理计划任务。

```python
class ScheduledTask(models.Model):
    TASK_TYPES = [
        ("sync_geo_ip", "同步 GeoIP 池"),
        ("sync_threat_intel", "同步威胁情报"),
        ("snapshot_reputation", "IP 信誉快照"),
        ("cleanup_logs", "清理旧日志"),
        ("custom", "自定义命令"),
    ]

    name = models.CharField(max_length=100)
    task_type = models.CharField(max_length=50, choices=TASK_TYPES)

    # 调度
    cron_expression = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    # 任务配置
    command = models.CharField(max_length=500, blank=True)
    arguments = models.TextField(blank=True)

    # 状态
    last_run_at = models.DateTimeField(null=True, blank=True)
    last_status = models.CharField(max_length=20, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### 使用示例

```python
from django_ip_safeguard.models import ScheduledTask

# 创建计划任务
task = ScheduledTask.objects.create(
    name="每日 GeoIP 同步",
    task_type="sync_geo_ip",
    cron_expression="0 2 * * *",  # 每天凌晨 2 点
)
```

## TaskExecutionLog

记录任务执行历史。

```python
class TaskExecutionLog(models.Model):
    STATUS_CHOICES = [
        ("pending", "等待中"),
        ("running", "运行中"),
        ("success", "成功"),
        ("failed", "失败"),
        ("timeout", "超时"),
    ]

    task = models.ForeignKey(ScheduledTask, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    output = models.TextField(blank=True)
    error = models.TextField(blank=True)

    duration = models.FloatField(null=True, blank=True)  # 秒
```

## UserProfile

支持 2FA 的扩展用户资料。

```python
class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    # 2FA 设置
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=32, blank=True)
    two_factor_methods = models.JSONField(default=list)

    # 安全
    login_history = models.JSONField(default=list)
    blocked_until = models.DateTimeField(null=True, blank=True)

    # 偏好设置
    language = models.CharField(max_length=10, default="en")
    theme = models.CharField(max_length=20, default="light")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

## Admin 界面

所有模型都已在 Django admin 中注册以便管理：

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
