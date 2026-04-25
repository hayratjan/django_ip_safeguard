# Django IP 风险拦截插件：开发与发布指南

## 1. 插件命名建议

你这个插件核心能力是「IP 风险识别 + 地区准入规则 + 自动封禁」。下面是可选命名：

- `django-ip-safeguard`（推荐，语义清晰、专业、容易记忆）
- `django-ip-guardian`
- `django-ip-shield`
- `django-risk-ip-firewall`
- `django-geoip-access-guard`

> 推荐最终 PyPI 包名：`django-ip-safeguard`  
> 推荐 Python 模块名：`django_ip_safeguard`

---

## 2. 需求说明（PRD 简版）

## 2.1 目标

在 Django 请求进入业务视图前完成 IP 安全校验，阻断高风险 IP 或不在允许地区范围内的请求，并记录审计日志。

## 2.2 核心能力

1. **请求前置校验**  
   通过 Django Middleware 在请求早期执行 IP 风险查询与地区校验。

2. **IP 情报查询**  
   对接第三方 IP 风险/地理位置服务（可插拔 Provider）。

3. **缓存与持久化**  
   - 优先从 Redis 读取已查询结果（低延迟）  
   - 命中失败回源查询并写入 Redis  
   - 可选落库（数据库）用于审计与离线分析

4. **风险判定引擎**  
   支持策略：
   - 风险分阈值（如 `risk_score >= 70` 拦截）
   - 风险标签黑名单（代理/VPN/Tor/爬虫等）
   - 国家/地区白名单、黑名单

5. **封禁机制**  
   命中拦截后可执行：
   - 临时封禁（TTL）
   - 永久封禁
   - 返回可配置状态码（默认 `403`）与响应体

6. **审计与观测**  
   记录拦截原因、来源 IP、命中规则、查询结果、时间戳、请求路径。

## 2.3 非功能需求

- 高性能：请求链路增加延迟可控（例如 P95 < 15ms，缓存命中场景）
- 高可用：外部 IP 服务异常时支持降级策略（放行/阻断可配置）
- 可扩展：支持多家 IP 情报服务适配器
- 可运维：日志可观测，关键指标可接入 Prometheus/Sentry

## 2.4 建议配置项

- `IP_GUARD_ENABLED`
- `IP_GUARD_REDIS_URL`
- `IP_GUARD_CACHE_TTL`
- `IP_GUARD_PROVIDER` / `IP_GUARD_PROVIDER_API_KEY`
- `IP_GUARD_RISK_SCORE_THRESHOLD`
- `IP_GUARD_BLOCKED_COUNTRIES`
- `IP_GUARD_ALLOWED_COUNTRIES`
- `IP_GUARD_FAIL_OPEN`（外部服务失败时是否默认放行）
- `IP_GUARD_BAN_TTL`
- `IP_GUARD_TRUSTED_PROXY_CIDRS`

---

## 3. 开发流程（建议里程碑）

## 阶段 1：最小可用版本（MVP）

1. 建立 Django App 基础结构：
   - `apps.py`
   - `middleware.py`
   - `services/provider.py`
   - `services/risk_engine.py`
   - `models.py`（可选）
   - `conf.py`（默认配置）

2. 实现中间件流程：
   - 提取客户端真实 IP（支持反向代理头）
   - 查询 Redis 缓存
   - 未命中则调用 IP Provider
   - 风险与地区判定
   - 命中拦截则返回 `403`

3. 完成基础单测：
   - 缓存命中/未命中
   - 风险阈值拦截
   - 国家黑白名单判定
   - Provider 异常降级

## 阶段 2：增强能力

1. 加入封禁表与审计日志表（可选）
2. 增加管理后台（Django Admin）查看 IP 记录和封禁状态
3. 增加信号与回调，支持业务自定义拦截逻辑
4. 指标埋点：请求总数、拦截数、命中率、Provider 延迟

## 阶段 3：工程化与发布准备

1. 补齐文档（快速开始、配置说明、FAQ）
2. 覆盖 CI（lint + test + build）
3. 进行语义化版本管理（SemVer）
4. 准备 PyPI 发布材料

---

## 4. 包结构建议

```text
django_ip_safeguard/
  __init__.py
  apps.py
  conf.py
  middleware.py
  exceptions.py
  types.py
  services/
    __init__.py
    provider_base.py
    provider_xxx.py
    risk_engine.py
    cache.py
  models.py
  admin.py
  migrations/
tests/
docs/
pyproject.toml
README.md
LICENSE
```

---

## 5. PyPI 发布流程（详细）

## 5.1 准备账号与凭据

1. 注册账号：
   - TestPyPI: [https://test.pypi.org/](https://test.pypi.org/)
   - PyPI: [https://pypi.org/](https://pypi.org/)

2. 开启 2FA（建议强制开启）
3. 创建 API Token：
   - TestPyPI token
   - PyPI token

## 5.2 配置项目元数据（`pyproject.toml`）

关键字段建议：

- `name = "django-ip-safeguard"`
- `version = "0.1.0"`
- `description`
- `readme = "README.md"`
- `requires-python = ">=3.9"`
- `dependencies`（如 `Django>=4.2`, `redis>=5.0.0`, `httpx>=0.27.0`）
- `classifiers`
- `license`
- `project.urls`

## 5.3 本地构建与检查

```bash
python -m pip install --upgrade build twine
python -m build
twine check dist/*
```

成功后会生成：
- `dist/*.whl`
- `dist/*.tar.gz`

## 5.4 先发布到 TestPyPI 验证

```bash
twine upload --repository testpypi dist/*
```

安装验证：

```bash
pip install -i https://test.pypi.org/simple/ django-ip-safeguard
```

## 5.5 正式发布到 PyPI

```bash
twine upload dist/*
```

建议使用环境变量传 token：

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-xxxxxxxxxxxxxxxx
twine upload dist/*
```

## 5.6 发布后检查

1. 在 PyPI 页面确认描述与版本正确
2. 新建干净虚拟环境进行安装回归：
   - `pip install django-ip-safeguard==0.1.0`
3. 运行最小 Django Demo 验证中间件可工作

## 5.7 版本迭代规范（推荐）

- `0.1.0`：首个可用版本
- `0.1.1`：仅修复问题
- `0.2.0`：新增兼容性功能
- `1.0.0`：接口稳定、可生产使用

发布节奏建议：

1. 修改版本号
2. 更新 `CHANGELOG.md`
3. 重新构建并执行测试
4. 发布到 TestPyPI
5. 验证通过后发布正式 PyPI

---

## 6. 验收清单

- [ ] 中间件可正确识别客户端真实 IP
- [ ] Redis 缓存生效，重复请求不重复查情报
- [ ] 风险阈值、标签、地区策略可配置
- [ ] 命中风险策略可成功阻断并返回自定义响应
- [ ] Provider 异常时降级策略符合预期
- [ ] 审计日志可追踪到每次拦截原因
- [ ] 单测覆盖核心判定链路
- [ ] TestPyPI 与 PyPI 发布成功

---

## 7. 主要功能与实现方案（可直接开发）

## 7.1 请求处理主链路

1. `IpGuardMiddleware` 在请求进入视图前执行。
2. 通过 `X-Forwarded-For` + `REMOTE_ADDR` 提取真实客户端 IP（仅信任配置的代理网段）。
3. 查询封禁缓存（Redis `ban:{ip}`）：
   - 命中：直接返回拦截响应。
   - 未命中：继续。
4. 查询情报缓存（Redis `intel:{ip}`）：
   - 命中：使用缓存结果。
   - 未命中：调用 Provider 获取风险/地区信息并回写缓存。
5. 调用风险引擎判定：
   - 风险分超阈值或命中风险标签 -> 拦截。
   - 地区不符合白/黑名单规则 -> 拦截。
6. 命中拦截时：
   - 写入封禁缓存（可配置 TTL）
   - 可选写入数据库审计表
   - 返回 `403` 或自定义响应
7. 放行请求进入业务视图。

## 7.2 核心模块拆分

- `middleware.py`：请求拦截入口与主流程编排
- `services/ip_resolver.py`：客户端真实 IP 提取与校验
- `services/cache.py`：Redis 读写封装
- `services/provider_base.py`：Provider 抽象基类
- `services/provider_http.py`：HTTP Provider 默认实现
- `services/risk_engine.py`：风险与地区策略判定
- `services/ban_service.py`：封禁写入与解除能力
- `models.py`：`IpAccessLog`、`IpBanRecord`（可选）
- `conf.py`：插件配置读取与默认值

## 7.3 数据模型建议（可选落库）

1. `IpAccessLog`
   - `ip`
   - `country_code`
   - `risk_score`
   - `risk_tags`
   - `decision`（allow/block）
   - `reason`
   - `path`
   - `created_at`

2. `IpBanRecord`
   - `ip`
   - `ban_reason`
   - `ban_source`（rule/manual）
   - `expired_at`
   - `is_active`
   - `created_at`

## 7.4 关键设计决策

- **优先缓存**：所有请求先查 Redis，降低外部 API 依赖与延迟。
- **Provider 可插拔**：后续切换不同 IP 服务不影响核心流程。
- **失败可降级**：外部服务故障时按配置 `FAIL_OPEN/FAIL_CLOSE` 处理。
- **规则可扩展**：风险分、标签、地区策略统一在风险引擎实现，便于新增规则。

---

## 8. 开发前准备清单（马上执行）

## 8.1 本地环境

- Python `>=3.9`
- Django `>=4.2`
- Redis `>=6`
- 推荐工具：`ruff`、`pytest`、`pytest-django`、`mypy`（可选）

## 8.2 工程初始化

- [ ] 初始化 `pyproject.toml`
- [ ] 初始化包结构 `django_ip_safeguard/`
- [ ] 增加基础 `README.md`、`CHANGELOG.md`、`LICENSE`
- [ ] 增加 `tests/` 测试目录
- [ ] 增加 `.gitignore` 与 CI 工作流

## 8.3 运行与联调资源

- [ ] 准备一个本地 Django 示例项目（用于联调中间件）
- [ ] 准备 Redis 实例（本地或 Docker）
- [ ] 准备一个测试用 IP 情报 API Key（沙箱/免费版本）

## 8.4 发布准备

- [ ] 创建 TestPyPI 与 PyPI 账号
- [ ] 创建 API Token
- [ ] 配置本地发布环境变量
- [ ] 完成 `python -m build` 与 `twine check`

---

## 9. 工作流程（执行节奏）

## 9.1 第一周：MVP 闭环

1. Day 1：完成项目骨架与配置模块
2. Day 2：实现 `ip_resolver` + `cache` 能力
3. Day 3：实现 Provider 与风险引擎
4. Day 4：实现 Middleware 与拦截响应
5. Day 5：补齐单测并在示例项目联调

## 9.2 第二周：可发布版本

1. 增加可选数据库审计模型
2. 完善日志、异常与降级策略
3. 补充文档（快速开始 + 配置说明 + FAQ）
4. 打包并发布到 TestPyPI 验证
5. 发布 `0.1.0` 到正式 PyPI

## 9.3 每次迭代固定流程

1. 更新需求与规则清单
2. 实现代码 + 编写测试
3. 本地验证（lint + test）
4. 更新文档与变更记录
5. 构建并发布

---

## 10. 开工命令模板

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e ".[dev]"
pytest -q
ruff check .
python -m build
```

---

## 11. 当前真实开发进展（已完成）

- 已完成 Provider 工厂：支持按配置切换 `dummy` 与 `http` Provider。
- 已完成 HTTP Provider 基础实现：支持 `endpoint`、`api_key`、`timeout`、自定义请求头。
- 已完成 HTTP Provider 重试：支持最大重试次数与指数退避。
- 已完成中间件接入 Provider 工厂：无需改代码，只通过 Django `settings` 即可切换实现。
- 已完成按路径降级策略：支持 `fail_open_path_prefixes` 与 `fail_close_path_prefixes`。
- 已完成数据库审计写入开关：`IP_GUARD_USE_DB_LOG=True` 时记录放行/拦截决策。
- 已补充 Provider 相关单测：覆盖工厂构建与 HTTP 返回数据解析流程。
- 已补充中间件策略单测：覆盖按路径放行/阻断的降级策略判断。

当前待继续事项：

1. 增加中间件集成测试（RequestFactory + Redis mock）
2. 增加缓存穿透保护（同 IP 并发去重锁）
3. 完成 Admin 审计筛选与批量封禁工具

