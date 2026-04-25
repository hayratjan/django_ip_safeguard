# 07 IP 情报 Provider 与风险引擎

## 7.1 数据类型：`IpIntel`

情报结果在代码中为数据结构（`django_ip_safeguard.types.IpIntel`），主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `ip` | str | 查询的目标 IP |
| `country_code` | str | ISO2 国家码，如 `CN`；未知时常为 `UNKNOWN` |
| `country_name` | str | 国家名称，如 `China` |
| `region` | str | 省份/地区 |
| `city` | str | 城市 |
| `latitude` | float | 纬度 |
| `longitude` | float | 经度 |
| `asn` | int | ASN 编号 |
| `asn_org` | str | ASN 组织名称 |
| `is_datacenter` | bool | 是否为数据中心 IP |
| `is_proxy` | bool | 是否为代理 IP |
| `is_vpn` | bool | 是否为 VPN IP |
| `is_tor` | bool | 是否为 Tor 出口节点 |
| `is_botnet` | bool | 是否为僵尸网络 IP |
| `risk_score` | int | 风险分数，数值越大风险越高 |
| `risk_tags` | list[str] | 风险标签，如 `tor`、`vpn`、`proxy`、`datacenter`、`botnet`、`subnet_attack`、`cdn` |
| `source` | str | 情报来源标识：`dummy` / `http` / `geoip2_local` / `chain_merged` 等 |

Redis 缓存与审计写库均基于该结构序列化。

---

## 7.2 Provider 类型

### 7.2.1 `dummy`（开发默认）

- 类：`DummyIpIntelProvider`
- 行为：对任意 IP 返回 `country_code="UNKNOWN"`、`risk_score=0`、无标签。
- 用途：本地开发与 CI，不发起外网请求。

### 7.2.2 `http`（生产对接）

- 类：`HttpIpIntelProvider`
- 配置：`IP_GUARD_PROVIDER=http`，并设置 `IP_GUARD_PROVIDER_ENDPOINT` 等。
- 请求方式：`GET {endpoint}?ip={ip}`
- 请求头：合并 `IP_GUARD_PROVIDER_HEADERS`；若配置了 `api_key` 且未显式写 `Authorization`，则自动加 `Authorization: Bearer {api_key}`。
- 期望响应：**JSON**，字段：
  - `country_code`（字符串，会转大写）
  - `risk_score`（整数，缺省为 0）
  - `risk_tags`（数组，缺省为空列表）

- 重试：最多 `max_retries + 1` 次尝试；失败间隔指数退避 `retry_backoff * 2^attempt` 秒。
- 异常：抛出 `ProviderError`，由中间件捕获后计入熔断失败次数并走失败降级。

### 7.2.3 `geoip2`（本地离线查询）

- 类：`GeoIP2LocalProvider`
- 配置：`IP_GUARD_GEOIP2_ENABLED=True`，设置 `IP_GUARD_GEOIP2_CITY_DB_PATH` 和 `IP_GUARD_GEOIP2_ASN_DB_PATH`。
- 行为：基于 MaxMind GeoLite2 数据库进行本地离线查询，零网络延迟。
- 返回字段：国家码、国家名、省份、城市、经纬度、ASN 编号、ASN 组织。
- 限制：不提供风险分数和风险标签（需配合其他 Provider 或本地风险引擎）。
- 数据库下载：`python manage.py download_geoip2_db`

**对接自有风控服务时**，请保证接口稳定、超时合理，且 JSON 与上述字段兼容（可在网关做字段映射）。

---

## 7.3 多 Provider 降级链

### 7.3.1 `ChainedProvider`

- 类：`ChainedProvider`
- 配置：`IP_GUARD_PROVIDER_CHAIN_ENABLED=True`，设置 `IP_GUARD_PROVIDER_CHAIN_NAMES`。
- 行为：依次尝试每个 Provider，支持两种模式：
  - **合并模式**（默认）：合并所有成功 Provider 的结果，前者缺失的字段由后者补充，风险分取最高值，风险标签取并集。
  - **降级模式**：使用第一个成功返回有效结果的 Provider。

### 7.3.2 自动降级链

当 `IP_GUARD_GEOIP2_ENABLED=True` 但未启用降级链时，系统自动构建 `http + geoip2` 降级链，确保在线 Provider 失败时仍可获取地理位置信息。

### 7.3.3 Provider 工厂

- 文件：`services/provider_factory.py`
- 函数：`build_provider(config)`
- 根据 `config.provider` 和降级链配置返回对应 Provider 实例。

---

## 7.4 本地风险规则引擎

### 7.4.1 `LocalRiskRuleEngine`

- 文件：`services/local_risk_engine.py`
- 配置：`IP_GUARD_LOCAL_RISK_ENGINE_ENABLED=True`
- 行为：不依赖外部 API 即可判定的本地规则，在 Provider 查询后执行。

### 7.4.2 规则列表

| 规则 | 检测方式 | 风险标签 | 风险加分 |
|------|---------|---------|---------|
| Tor 出口节点 | 从威胁情报同步的 Tor 节点列表匹配 | `tor` | +20 |
| 僵尸网络 CIDR | 从威胁情报同步的 botnet CIDR 列表匹配 | `botnet` | +20 |
| 数据中心 ASN | 本地已知数据中心 ASN 列表匹配 | `datacenter` | +20 |
| 代理/VPN 节点 | 从威胁情报同步的代理列表匹配 | `proxy` | +20 |
| 同 C 段攻击关联 | 统计同 /24 子网内不同 IP 数量 | `subnet_attack` | +20 |

### 7.4.3 ASN 识别服务

- 类：`AsnLookupService`
- 文件：`services/asn_lookup.py`
- 内置 30+ 知名数据中心 ASN（AWS、Azure、Cloudflare、阿里云、腾讯云、华为云等）
- 内置 10+ 知名 CDN ASN（Cloudflare CDN、Akamai、Fastly 等）
- 自动标记数据中心 IP 和 CDN IP

---

## 7.5 风险引擎：`evaluate_ip_risk`

- 文件：`services/risk_engine.py`
- 输入：`IpIntel`、`IpGuardSettings`（运行时策略）
- 输出：`RiskDecision(allow, reason, should_ban, ban_ttl, local_risk_reasons)`

判定顺序（短路）：

1. **`risk_score >= risk_score_threshold`** → 不允许；`should_ban=True`（中间件会写入封禁）。
2. **`risk_tags` 与 `blocked_risk_tags` 有交集**（大小写不敏感）→ 不允许；`should_ban=True`。
3. **`allowed_countries` 非空** 且 `country_code` 不在其中 → 不允许；`should_ban=False`。
4. **`blocked_countries` 非空** 且 `country_code` 在其中 → 不允许；`should_ban=False`。
5. 否则允许。

**注意**：国家规则依赖情报中的 `country_code`；若 Provider 返回 `UNKNOWN`，白名单策略可能导致「非名单即拦截」——请评估是否配合地理池或更换 Provider。

---

## 7.6 IP 关联分析服务

### 7.6.1 `IpCorrelationService`

- 文件：`services/ip_correlation.py`
- 配置：`IP_GUARD_IP_CORRELATION_ENABLED=True`
- 功能：
  - 记录每个 IP 的访问行为（拦截/放行）
  - 统计同 C 段（/24）和 B 段（/16）的访问热度
  - 检测子网攻击关联（高拦截率的子网）
  - 提供热门攻击子网排行

### 7.6.2 子网攻击检测

当同 /24 子网内出现大量不同 IP 且拦截率较高时，标记为子网攻击关联，自动提升风险分数。

---

## 7.7 分层缓存架构

### 7.7.1 `LayeredCacheService`

- 文件：`services/layered_cache.py`
- 配置：`IP_GUARD_L1_CACHE_ENABLED=True`

分层缓存查询顺序：

| 层级 | 存储 | TTL | 说明 |
|------|------|-----|------|
| L1 | 进程内字典 | 10s | 热点 IP 极速响应 |
| L2 | Redis | 1800-7200s | 持久化缓存，按风险分级 TTL |
| L3 | GeoLite2 本地数据库 | 持久 | 离线查询，零网络延迟 |
| L4 | HTTP API Provider | 实时 | 外部情报查询 |

### 7.7.2 缓存策略

- 高风险 IP（`risk_score >= threshold`）：缓存 7200 秒
- 低风险 IP：缓存 1800 秒
- L1 缓存满时自动淘汰过期和最早条目
- 封禁状态和限流计数始终走 Redis（L2）

---

## 7.8 Provider 失败与熔断

当 HTTP 请求抛错或超时时：

1. 中间件增加 Redis 中的失败计数（键见 [08](./08-Redis缓存封禁限流与熔断.md)）。
2. 若计数 ≥ `provider_circuit_breaker_failures`，在 TTL 窗口内视为熔断打开，**跳过**外部请求，直接失败降级。
3. 成功一次情报拉取后清零失败计数。

失败降级路径使用 `should_fail_open(path, ...)`：

- 若路径命中 `fail_close_path_prefixes` → **不放行**（返回 JSON 提示服务不可用）。
- 若路径命中 `fail_open_path_prefixes` → **放行**。
- 否则使用全局 `fail_open`。

---

## 7.9 相关文档

- 配置：[04-配置项完整参考](./04-配置项完整参考.md)
- 中间件：[03-中间件与请求判定流程](./03-中间件与请求判定流程.md)
- Redis：[08-Redis缓存封禁限流与熔断](./08-Redis缓存封禁限流与熔断.md)
- 管理命令：[14-管理命令与定时任务](./14-管理命令与定时任务.md)
