# 配置项完整参考

## 完整设置

Django IP Safeguard 的所有配置选项都在 Django 设置的 `IP_GUARD` 字典中。

```python
IP_GUARD = {
    # 核心设置
    "ENABLED": True,
    "DEBUG": False,

    # IP 过滤
    "WHITELIST_IPS": [],
    "BLACKLIST_IPS": [],
    "TRUSTED_PROXIES": [],

    # 默认策略
    "DEFAULT_POLICY": "allow",

    # ... 更多设置
}
```

## 核心设置

### ENABLED

- **类型**: `bool`
- **默认值**: `True`
- **描述**: 启用或禁用 IP Guard 中间件。

### DEBUG

- **类型**: `bool`
- **默认值**: `False`
- **描述**: 启用调试模式以获取额外日志。

## IP 过滤

### WHITELIST_IPS

- **类型**: `list[str]`
- **默认值**: `[]`
- **描述**: 绕过所有检查的 IP 地址或 CIDR 范围列表。

```python
IP_GUARD = {
    "WHITELIST_IPS": [
        "127.0.0.1",
        "10.0.0.0/8",
        "192.168.1.0/24",
    ],
}
```

### BLACKLIST_IPS

- **类型**: `list[str]`
- **默认值**: `[]`
- **描述**: 始终被阻止的 IP 地址或 CIDR 范围列表。

### TRUSTED_PROXIES

- **类型**: `list[str]`
- **默认值**: `[]`
- **描述**: 用于 X-Forwarded-For 解析的信任代理 IP 地址列表。

### DEFAULT_POLICY

- **类型**: `str`
- **默认值**: `"allow"`
- **选项**: `"allow"`, `"deny"`
- **描述**: 当没有规则匹配时的默认策略。

## 认证设置

### ENABLE_2FA

- **类型**: `bool`
- **默认值**: `True`
- **描述**: 为管理员用户启用双因素认证。

### ENABLE_API_KEY

- **类型**: `bool`
- **默认值**: `True`
- **描述**: 启用 API 密钥认证。

## JWT 设置

```python
IP_GUARD = {
    "JWT": {
        "SECRET_KEY": "your-secret-key",
        "ACCESS_TOKEN_LIFETIME_MINUTES": 60,
        "REFRESH_TOKEN_LIFETIME_DAYS": 7,
        "ALGORITHM": "HS256",
    },
}
```

### JWT.SECRET_KEY

- **类型**: `str`
- **必填**: 是
- **描述**: JWT 签名的密钥。**生产环境必须更改！**

### JWT.ACCESS_TOKEN_LIFETIME_MINUTES

- **类型**: `int`
- **默认值**: `60`
- **描述**: JWT 访问令牌生命周期（分钟）。

### JWT.REFRESH_TOKEN_LIFETIME_DAYS

- **类型**: `int`
- **默认值**: `7`
- **描述**: JWT 刷新令牌生命周期（天）。

## 缓存设置

```python
IP_GUARD = {
    "CACHE": {
        "ENABLED": True,
        "BACKEND": "redis",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "TIMEOUT": 300,
    },
}
```

### CACHE.ENABLED

- **类型**: `bool`
- **默认值**: `True`
- **描述**: 启用 IP 查询缓存。

### CACHE.BACKEND

- **类型**: `str`
- **默认值**: `"redis"`
- **选项**: `"redis"`, `"locmem"`, `"database"`
- **描述**: 使用的缓存后端。

### CACHE.LOCATION

- **类型**: `str`
- **默认值**: `"redis://127.0.0.1:6379/1"`
- **描述**: 缓存位置（Redis URL 或数据库表名）。

### CACHE.TIMEOUT

- **类型**: `int`
- **默认值**: `300`
- **描述**: 默认缓存超时（秒）。

## 限流设置

```python
IP_GUARD = {
    "RATE_LIMIT": {
        "ENABLED": True,
        "REQUESTS_PER_MINUTE": 60,
        "BURST": 10,
    },
}
```

### RATE_LIMIT.ENABLED

- **类型**: `bool`
- **默认值**: `True`
- **描述**: 启用限流。

### RATE_LIMIT.REQUESTS_PER_MINUTE

- **类型**: `int`
- **默认值**: `60`
- **描述**: 每个 IP 每分钟最大请求数。

## 自动封禁设置

```python
IP_GUARD = {
    "AUTO_BAN": {
        "ENABLED": True,
        "THRESHOLD": 5,
        "DURATION_MINUTES": 30,
        "TRACK_FAILED_AUTH": True,
    },
}
```

### AUTO_BAN.ENABLED

- **类型**: `bool`
- **默认值**: `True`
- **描述**: 启用自动 IP 封禁。

### AUTO_BAN.THRESHOLD

- **类型**: `int`
- **默认值**: `5`
- **描述**: 自动封禁前的失败尝试次数。

### AUTO_BAN.DURATION_MINUTES

- **类型**: `int`
- **默认值**: `30`
- **描述**: 封禁时长（分钟）。

## 风险引擎设置

```python
IP_GUARD = {
    "RISK_ENGINE": {
        "ENABLED": True,
        "PROVIDERS": ["local", "http"],
        "CONFIDENCE_THRESHOLD": 0.5,
    },
}
```

### RISK_ENGINE.ENABLED

- **类型**: `bool`
- **默认值**: `True`
- **描述**: 启用风险评估。

### RISK_ENGINE.PROVIDERS

- **类型**: `list[str]`
- **默认值**: `["local", "http"]`
- **描述**: 要使用的风险评估提供者。

## GeoIP 设置

```python
IP_GUARD = {
    "GEOIP": {
        "ENABLED": True,
        "DB_PATH": "/path/to/geoip.mmdb",
        "ALLOWED_COUNTRIES": [],
        "BLOCKED_COUNTRIES": [],
    },
}
```

### GEOIP.ENABLED

- **类型**: `bool`
- **默认值**: `True`
- **描述**: 启用 GeoIP 封禁。

### GEOIP.DB_PATH

- **类型**: `str`
- **默认值**: `None`
- **描述**: GeoIP 数据库文件路径。

### GEOIP.ALLOWED_COUNTRIES

- **类型**: `list[str]`
- **默认值**: `[]`
- **描述**: 允许的国家代码列表（ISO 3166-1 alpha-2）。

### GEOIP.BLOCKED_COUNTRIES

- **类型**: `list[str]`
- **默认值**: `[]`
- **描述**: 阻止的国家代码列表（ISO 3166-1 alpha-2）。

## 威胁情报设置

```python
IP_GUARD = {
    "THREAT_INTEL": {
        "ENABLED": True,
        "SUBSCRIBE_URLS": [],
        "SYNC_INTERVAL_MINUTES": 60,
    },
}
```

## 熔断器设置

```python
IP_GUARD = {
    "CIRCUIT_BREAKER": {
        "ENABLED": True,
        "FAILURE_THRESHOLD": 5,
        "RECOVERY_TIMEOUT": 60,
        "EXPECTED_EXCEPTION": "requests.exceptions.RequestException",
    },
}
```

## 阻止响应设置

```python
IP_GUARD = {
    "BLOCK_RESPONSE": {
        "status_code": 403,
        "content": "访问被拒绝",
        "content_type": "text/plain",
    },
}
```

## 日志设置

```python
IP_GUARD = {
    "LOGGING": {
        "ENABLED": True,
        "LEVEL": "INFO",
        "LOG_FAILED_AUTH": True,
        "LOG_BLOCKED_IPS": True,
    },
}
```

## 完整示例

```python
IP_GUARD = {
    "ENABLED": True,
    "DEBUG": False,

    "WHITELIST_IPS": ["127.0.0.1", "10.0.0.0/8"],
    "BLACKLIST_IPS": [],
    "TRUSTED_PROXIES": ["10.0.0.0/8"],
    "DEFAULT_POLICY": "allow",

    "ENABLE_2FA": True,
    "ENABLE_API_KEY": True,

    "JWT": {
        "SECRET_KEY": "change-this-in-production",
        "ACCESS_TOKEN_LIFETIME_MINUTES": 60,
        "REFRESH_TOKEN_LIFETIME_DAYS": 7,
    },

    "CACHE": {
        "ENABLED": True,
        "BACKEND": "redis",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "TIMEOUT": 300,
    },

    "RATE_LIMIT": {
        "ENABLED": True,
        "REQUESTS_PER_MINUTE": 60,
    },

    "AUTO_BAN": {
        "ENABLED": True,
        "THRESHOLD": 5,
        "DURATION_MINUTES": 30,
    },

    "RISK_ENGINE": {
        "ENABLED": True,
        "PROVIDERS": ["local", "http"],
    },

    "GEOIP": {
        "ENABLED": True,
        "BLOCKED_COUNTRIES": ["CN", "RU"],
    },

    "LOGGING": {
        "ENABLED": True,
        "LEVEL": "INFO",
    },
}
```

## 策略引擎 v2（v0.2.0+）

策略引擎 v2 把"风险阈值"细化为"加权打分 + 分级动作"，并支持多策略路由。下列字段既可写在 `IP_GUARD` 字典里作为全局默认，也可按策略行覆盖（数据库 `IpGuardPolicy` 同名字段优先于全局配置）。

### 跳过路径与基础

| 配置项 | 默认 | 说明 |
|--------|------|------|
| `SKIP_PATH_PREFIXES` | `[]` | 跳过中间件判定的路径前缀（如 `/healthz`），适合健康检查 / Webhook |

### 多策略路由

| 配置项 | 默认 | 说明 |
|--------|------|------|
| `POLICY_NAME` | `default` | 全局兜底策略名，也是 ORM 行 `name` 字段 |
| `POLICY_PRIORITY` | `10000` | 数值越小越优先；自建策略请填更小值 |
| `MATCH_HOST_REGEX` | `""` | 命中 `request.get_host()` 去掉端口后的主机名才生效；空表示不限制 |
| `MATCH_PATH_PREFIXES` | `[]` | 路径前缀；任一命中即生效；空表示不限制 |
| `MATCH_METHODS` | `[]` | HTTP 方法白名单；空表示不限制 |

### 加权分与分级动作

| 配置项 | 默认 | 说明 |
|--------|------|------|
| `TIER_MEDIUM` | `40` | 中等风险阈值；`score < TIER_MEDIUM` 时直接放行 |
| `TIER_HIGH` | `70` | 高风险阈值；`score >= TIER_HIGH` 时执行 `HIGH_ACTION` |
| `MEDIUM_ACTION` | `block` | 中等风险动作（`allow` / `log_only` / `rate_limit` / `challenge` / `block` / `ban`） |
| `HIGH_ACTION` | `ban` | 高风险动作 |
| `CHALLENGE_STATUS_CODE` | `403` | `action=challenge` 时返回的状态码，建议 `429` |
| `SIGNAL_WEIGHTS` | 见下表 | 各风险信号的权重；策略行 `signal_weights` 可逐条覆盖 |

#### 默认信号权重 `SIGNAL_WEIGHTS`

| 信号键 | 默认权重 | 命中时贡献 | 说明 |
|--------|----------|-----------|------|
| `risk_score` | `1.0` | `risk_score × 1` | 情报源原始分（0~100） |
| `tag_blocked` | `50.0` | 50 | 命中 `BLOCKED_RISK_TAGS` 中任一 |
| `country_blocked` | `60.0` | 60 | 命中 `BLOCKED_COUNTRIES` |
| `country_not_allowed` | `60.0` | 60 | 配置了 `ALLOWED_COUNTRIES` 但当前国家不在白名单 |
| `geo_pool` | `30.0` | 30 | 命中 GEO 池规则（china/international） |
| `rate_limit_hit` | `40.0` | 40 | 触发限速 |
| `reputation_rising` | `20.0` | 20 | IP 信誉持续走低（v0.2.x 后续版本启用） |
| `tor` | `35.0` | 35 | Tor 出口节点 |
| `datacenter` | `15.0` | 15 | 数据中心 ASN |
| `botnet` | `70.0` | 70 | 已知 botnet IP |

> 不需要的信号将权重设为 `0` 即可。

### 多策略示例（settings.py 配 + DB 多行）

```python
# settings.py：全局默认（兜底策略 + 通用阈值）
IP_GUARD = {
    "ENABLED": True,
    "TIER_MEDIUM": 40,
    "TIER_HIGH": 70,
    "MEDIUM_ACTION": "block",
    "HIGH_ACTION": "ban",
    "CHALLENGE_STATUS_CODE": 429,
    "SKIP_PATH_PREFIXES": ["/healthz"],
}
```

```python
# 通过 Admin 或 ORM 创建策略行（priority 越小越优先）：
from django_ip_safeguard.models import IpGuardPolicy

IpGuardPolicy.objects.create(
    name="api-write",
    priority=100,
    match_host_regex=r"^api\.",
    match_path_prefixes=["/api/"],
    match_methods=["POST", "PUT", "DELETE"],
    medium_action="challenge",
    high_action="ban",
    tier_thresholds={"medium": 30, "high": 60},
    signal_weights={"tag_blocked": 80, "tor": 50},
)
```

策略保存时会在 `IpGuardPolicySnapshot` 写入"变更前/变更后"快照（含操作人），便于审计与回滚。
