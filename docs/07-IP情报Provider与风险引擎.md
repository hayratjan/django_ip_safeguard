# 07 IP 情报 Provider 与风险引擎

## 7.1 数据类型：`IpIntel`

情报结果在代码中为不可变数据结构（`django_ip_safeguard.types.IpIntel`），主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `ip` | str | 查询的目标 IP |
| `country_code` | str | ISO2 国家码，如 `CN`；未知时常为 `UNKNOWN` |
| `risk_score` | int | 风险分数，数值越大风险越高（具体区间由 Provider 定义） |
| `risk_tags` | list[str] | 风险标签，如 `tor`、`vpn`、`proxy` |
| `source` | str | 情报来源标识：`dummy` / `http` / `policy` 等 |

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

**对接自有风控服务时**，请保证接口稳定、超时合理，且 JSON 与上述字段兼容（可在网关做字段映射）。

---

## 7.3 Provider 工厂

- 文件：`services/provider_factory.py`  
- 函数：`build_provider(config)`  
- 根据 `config.provider` 返回 `DummyIpIntelProvider` 或 `HttpIpIntelProvider` 实例。

---

## 7.4 风险引擎：`evaluate_ip_risk`

- 文件：`services/risk_engine.py`  
- 输入：`IpIntel`、`IpGuardSettings`（运行时策略）  
- 输出：`RiskDecision(allow, reason, should_ban, ban_ttl)`  

判定顺序（短路）：

1. **`risk_score >= risk_score_threshold`** → 不允许；`should_ban=True`（中间件会写入封禁）。  
2. **`risk_tags` 与 `blocked_risk_tags` 有交集**（大小写不敏感）→ 不允许；`should_ban=True`。  
3. **`allowed_countries` 非空** 且 `country_code` 不在其中 → 不允许；`should_ban=False`。  
4. **`blocked_countries` 非空** 且 `country_code` 在其中 → 不允许；`should_ban=False`。  
5. 否则允许。

**注意**：国家规则依赖情报中的 `country_code`；若 Provider 返回 `UNKNOWN`，白名单策略可能导致「非名单即拦截」——请评估是否配合地理池或更换 Provider。

---

## 7.5 Provider 失败与熔断

当 HTTP 请求抛错或超时时：

1. 中间件增加 Redis 中的失败计数（键见 [08](./08-Redis缓存封禁限流与熔断.md)）。  
2. 若计数 ≥ `provider_circuit_breaker_failures`，在 TTL 窗口内视为熔断打开，**跳过**外部请求，直接失败降级。  
3. 成功一次情报拉取后清零失败计数。

失败降级路径使用 `should_fail_open(path, ...)`：

- 若路径命中 `fail_close_path_prefixes` → **不放行**（返回 JSON 提示服务不可用）。  
- 若路径命中 `fail_open_path_prefixes` → **放行**。  
- 否则使用全局 `fail_open`。

---

## 7.6 相关文档

- 配置：[04-配置项完整参考](./04-配置项完整参考.md)  
- 中间件：[03-中间件与请求判定流程](./03-中间件与请求判定流程.md)  
- Redis：[08-Redis缓存封禁限流与熔断](./08-Redis缓存封禁限流与熔断.md)
