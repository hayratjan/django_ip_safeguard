# 数据库模型

## 概述

Django IP Safeguard 提供多个模型来管理 IP 策略、访问日志和认证。

## 模型概览

| 模型 | 描述 |
|------|------|
| `IpGuardPolicy` | 主要策略配置（v0.2.0 起支持多策略路由 + 加权打分） |
| `IpGuardPolicySnapshot` | 策略变更快照（保存前后字段，用于审计回滚，v0.2.0 新增） |
| `IpAccessLog` | 访问日志记录 |
| `IpBanRecord` | 封禁记录 |
| `ApiKey` | API 密钥存储 |
| `ApiKeyUsageLog` | API 密钥使用日志 |
| `ScheduledTask` | 计划任务定义 |
| `TaskExecutionLog` | 任务执行历史 |
| `UserProfile` | 扩展用户资料 |

## IpGuardPolicy（v0.2.0+）

策略行；可创建多条，由中间件按 `priority` 升序逐条匹配。重要字段：

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `name` | CharField(64) | `default` | 策略名（唯一） |
| `priority` | IntegerField | `10000` | 数值越小越优先；`default` 请保持较大值 |
| `enabled` | BooleanField | `True` | 是否启用 |
| `match_host_regex` | CharField(256) | `""` | Host 正则（不限端口部分） |
| `match_path_prefixes` | JSONField(list) | `[]` | 路径前缀；任一命中即生效 |
| `match_methods` | JSONField(list) | `[]` | HTTP 方法；空表示任意 |
| `risk_score_threshold` | IntegerField | `70` | 兼容旧版的硬阈值（高于此值直接 `ban`） |
| `tier_thresholds` | JSONField(dict) | `{}` | `{"medium":40,"high":70}`；缺省回退到 settings |
| `signal_weights` | JSONField(dict) | `{}` | 覆盖默认权重；空则使用 `policy_service.DEFAULT_SIGNAL_WEIGHTS` |
| `medium_action` | CharField | `block` | 中风险动作（allow/log_only/rate_limit/challenge/block/ban） |
| `high_action` | CharField | `ban` | 高风险动作 |
| `blocked_risk_tags` | JSONField(list) | `[]` | 命中即得 `tag_blocked` 权重分 |
| `allowed_countries` / `blocked_countries` | JSONField(list) | `[]` | ISO 国家码白/黑名单 |
| `ip_whitelist` / `ip_blacklist` | JSONField(list) | `[]` | IP / CIDR 列表 |
| `rate_limit_per_minute` | PositiveIntegerField | `0` | `0` 不启用 |
| `fail_open` | BooleanField | `True` | 情报源故障时是否放行 |
| `fail_open_path_prefixes` / `fail_close_path_prefixes` | JSONField(list) | `[]` | 按路径覆盖 fail-open 行为 |
| `block_status_code` | IntegerField | `403` | `block` / `ban` 响应状态码 |
| `cache_ttl` | IntegerField | `3600` | 情报缓存 TTL |
| `ban_ttl` | IntegerField | `86400` | 封禁 TTL |
| `use_db_log` | BooleanField | `False` | 是否额外写 `IpAccessLog`（控制 IO 成本） |
| `china_pool_rule` / `international_pool_rule` | CharField | `off` | 地理池规则 |
| `updated_at` | DateTimeField | auto | 更新时间 |

### 使用示例

```python
from django_ip_safeguard.models import IpGuardPolicy

# 1. 兜底策略（default）
default_policy, _ = IpGuardPolicy.objects.get_or_create(name="default")
default_policy.tier_thresholds = {"medium": 40, "high": 70}
default_policy.medium_action = "block"
default_policy.high_action = "ban"
default_policy.save()  # 触发 invalidate_policy_cache + Redis 广播

# 2. 单独保护写接口
IpGuardPolicy.objects.create(
    name="api-write",
    priority=100,
    match_host_regex=r"^api\.",
    match_path_prefixes=["/api/"],
    match_methods=["POST", "PUT", "DELETE"],
    medium_action="challenge",
    high_action="ban",
    tier_thresholds={"medium": 30, "high": 60},
    signal_weights={"tag_blocked": 80, "tor": 50, "country_blocked": 90},
)
```

策略行变更（Admin 或 `/api/policy/` API）会同步写入 `IpGuardPolicySnapshot`，并通过 Redis pubsub 通知其它 worker 立即清缓存。

## IpGuardPolicySnapshot（v0.2.0+）

| 字段 | 说明 |
|------|------|
| `policy` | 关联的 `IpGuardPolicy` |
| `actor` | 触发变更的 Django 用户（可空） |
| `before_json` | 变更前完整字段 JSON |
| `after_json` | 变更后完整字段 JSON |
| `created_at` | 变更时间 |

可通过 Django Admin 或后续即将开放的 `/api/policy/snapshots/` 接口查询、对比、回滚。


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
