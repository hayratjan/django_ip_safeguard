# 08 Redis 缓存、封禁、限流与熔断

## 8.1 封装类

- 文件：`django_ip_safeguard/services/cache.py`  
- 类：`RedisCacheService`  
- 连接：`redis.Redis.from_url(redis_url, decode_responses=True)`  

所有键均为字符串；JSON 情报使用 `decode_responses=True` 便于读写。

---

## 8.2 键名约定一览

| 逻辑 | Redis 键模式 | 说明 |
|------|----------------|------|
| 情报缓存 | `ip_guard:intel:{ip}` | JSON 序列化的 `IpIntel`，TTL 按高/低风险分别设置 |
| 封禁 | `ip_guard:ban:{ip}` | 存在即表示封禁；值为原因字符串；带 TTL |
| 情报去重锁 | `ip_guard:lock:intel:{ip}` | `SET NX EX`，防止并发击穿同一 IP |
| Provider 失败计数 | `ip_guard:provider:circuit_failures` | 整数自增，带过期时间窗口 |
| 单 IP 限流 | `ip_guard:ratelimit:{ip}` | 计数器，窗口 60 秒 |
| 地理池索引 | `ip_guard:geo_pool:data:{pool_key}` | `pool_key` 为 `china` 或 `international`；大 JSON，一般不设 TTL，由下次同步覆盖 |

---

## 8.3 情报缓存

- **读**：`get_ip_intel(ip)` → 反序列化为 `IpIntel` 或 `None`。  
- **写**：`set_ip_intel(ip_intel, ttl)` → `SETEX`。  
- **TTL 选择**（中间件内）：若 `risk_score >= threshold` 用 `high_risk_cache_ttl`，否则 `low_risk_cache_ttl`。

---

## 8.4 封禁

- **判断**：`is_banned(ip)` → 键存在即为真。  
- **写入**：`set_ban(ip, reason, ttl)` → `SETEX`。  
- **删除**：`unban(ip)` → `DEL`。  

封禁来源包括：

- 风险引擎判定 `should_ban=True` 时中间件调用 `ban_ip`；  
- 管理 API `POST /ip-guard/api/ban/` 写 Redis 并 upsert `IpBanRecord`。

---

## 8.5 单 IP 每分钟请求上限

- 方法：`is_rate_limited(ip, max_per_minute)`  
- `max_per_minute <= 0`：直接返回 `False`（功能关闭）。  
- 实现：`INCR ip_guard:ratelimit:{ip}`，若为首次则 `EXPIRE` **60 秒**。  
- 语义：自该 IP **首次**触发计数起 60 秒内累计次数；超过 `max_per_minute` 则返回 `True`（拦截）。

**注意**：这是「滑动窗口近似」的固定窗口实现，非令牌桶；对突发流量敏感时请调低阈值或在网关侧做更细粒度 QoS。

---

## 8.6 Provider 熔断计数

- **增加**：`increase_provider_failures(ttl)` → `INCR` 全局键；首次设置 `EXPIRE ttl`。  
- **读取**：`get_provider_failures()`  
- **清零**：`clear_provider_failures()`（成功拉到情报后调用）  

中间件在失败次数 ≥ `provider_circuit_breaker_failures` 时短路外部请求。

---

## 8.7 地理池数据

- **读**：`get_geo_pool_data(pool_key)`  
- **写**：`set_geo_pool_data(pool_key, dict)` → `SET`（持久至下次覆盖）  

进程内另有 `geo_ip_pool_runtime` 模块级缓存，见 [06](./06-地理IP池与定时同步.md)。

---

## 8.8 运维建议

- Redis 建议开启 **持久化（AOF/RDB）** 与 **哨兵/集群**，避免单点故障导致全站策略异常。  
- 定期监控 **内存用量**；地理池 JSON 与中国完整列表体积需纳入容量规划。  
- 关键指标：情报缓存命中率、Provider 失败率、限流触发次数、封禁键数量。

---

## 8.9 相关文档

- 配置：[04-配置项完整参考](./04-配置项完整参考.md)  
- 中间件：[03-中间件与请求判定流程](./03-中间件与请求判定流程.md)  
- 地理池：[06-地理IP池与定时同步](./06-地理IP池与定时同步.md)
