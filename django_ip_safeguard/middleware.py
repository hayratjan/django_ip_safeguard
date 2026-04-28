"""IP Guard 中间件。

新版要点（v0.2.0）：
- ``IP_GUARD_SKIP_PATH_PREFIXES``：完全跳过判定（如健康检查、Webhook）。
- 所有拦截响应都经 :mod:`action_executor` 集中构造，按 Accept 自动返回 JSON / HTML。
- 封禁分支补齐 :func:`log_access_decision`，与黑名单/风险分支保持一致。
- 情报锁竞争：拿不到锁短暂等待后重读缓存一次，仍无则按 fail-open/close 处理。
- 启动时尝试在后台订阅 Redis 策略失效通道，多 worker 场景下变更秒级生效。
"""

from __future__ import annotations

import logging
import time

from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _t

from django_ip_safeguard.conf import get_settings
from django_ip_safeguard.services.action_executor import build_response
from django_ip_safeguard.services.asn_lookup import AsnLookupService
from django_ip_safeguard.services.audit_service import log_access_decision, mask_ip
from django_ip_safeguard.services.ban_service import ban_ip
from django_ip_safeguard.services.cache import RedisCacheService
from django_ip_safeguard.services.circuit_breaker import CircuitBreaker
from django_ip_safeguard.services.geo_ip_pool_runtime import (
    evaluate_geo_ip_pool_rules,
    infer_country_from_pools,
)
from django_ip_safeguard.services.ip_matcher import first_matching_rule
from django_ip_safeguard.services.ip_resolver import resolve_client_ip
from django_ip_safeguard.services.layered_cache import LayeredCacheService
from django_ip_safeguard.services.policy_service import (
    load_effective_policy,
    start_policy_invalidate_subscriber,
)
from django_ip_safeguard.services.provider_factory import build_provider
from django_ip_safeguard.services.risk_engine import evaluate_ip_risk
from django_ip_safeguard.types import IpIntel


def _audit_request_meta(request):
    """审计日志附带登录用户与 HTTP 方法。"""
    return {"user": getattr(request, "user", None), "method": getattr(request, "method", "") or ""}

logger = logging.getLogger(__name__)


def should_fail_open(path: str, default_fail_open: bool, open_prefixes: tuple, close_prefixes: tuple) -> bool:
    for prefix in close_prefixes:
        if prefix and path.startswith(prefix):
            return False
    for prefix in open_prefixes:
        if prefix and path.startswith(prefix):
            return True
    return default_fail_open


def _path_in(prefixes: tuple, path: str) -> bool:
    return any(p and path.startswith(p) for p in prefixes)


class IpGuardMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response
        self.config = get_settings()
        self.cache_service = RedisCacheService(self.config.redis_url)

        if self.config.l1_cache_enabled:
            self.layered_cache = LayeredCacheService(
                redis_cache=self.cache_service,
                l1_ttl=self.config.l1_cache_ttl,
                l1_max_size=self.config.l1_cache_max_size,
            )
        else:
            self.layered_cache = None

        self.provider = build_provider(self.config)
        self.circuit_breaker = CircuitBreaker(
            cache_service=self.cache_service,
            failure_threshold=self.config.provider_circuit_breaker_failures,
            recovery_timeout=self.config.provider_circuit_breaker_ttl,
        )
        self.asn_lookup = AsnLookupService()

        self.local_risk_engine = None
        if self.config.local_risk_engine_enabled:
            from django_ip_safeguard.services.local_risk_engine import LocalRiskRuleEngine
            self.local_risk_engine = LocalRiskRuleEngine(self.cache_service, self.config)

        self.ip_correlation = None
        if self.config.ip_correlation_enabled:
            from django_ip_safeguard.services.ip_correlation import IpCorrelationService
            self.ip_correlation = IpCorrelationService(self.cache_service, self.config)

        # 多 worker 失效订阅；失败不影响主流程
        try:
            start_policy_invalidate_subscriber(self.config.redis_url)
        except Exception:  # noqa: BLE001
            pass

    def _get_intel_from_cache(self, ip: str):
        if self.layered_cache:
            return self.layered_cache.get_ip_intel(ip)
        return self.cache_service.get_ip_intel(ip)

    def _set_intel_to_cache(self, ip_intel: IpIntel, ttl: int) -> None:
        if self.layered_cache:
            self.layered_cache.set_ip_intel(ip_intel, ttl=ttl)
        else:
            self.cache_service.set_ip_intel(ip_intel, ttl=ttl)

    def _is_banned(self, ip: str) -> bool:
        if self.layered_cache:
            return self.layered_cache.is_banned(ip)
        return self.cache_service.is_banned(ip)

    def _is_rate_limited(self, ip: str, limit: int) -> bool:
        if self.layered_cache:
            return self.layered_cache.is_rate_limited(ip, limit)
        return self.cache_service.is_rate_limited(ip, limit)

    def _acquire_lock(self, ip: str, ttl: int) -> bool:
        if self.layered_cache:
            return self.layered_cache.acquire_intel_lock(ip, ttl)
        return self.cache_service.acquire_intel_lock(ip, ttl)

    def _release_lock(self, ip: str) -> None:
        if self.layered_cache:
            self.layered_cache.release_intel_lock(ip)
        else:
            self.cache_service.release_intel_lock(ip)

    def _build_block(self, request, runtime_config, *, ip, reason, action="block"):
        return build_response(request, action, reason, ip, runtime_config)

    def _record_skip_path(self, request):
        """跳过路径：不计 total，仅 skipped_paths / b_skip_path。"""
        if not self.config.metrics_redis_enabled and not self.config.structured_decision_logging:
            return
        try:
            from django_ip_safeguard.services.decision_metrics import record_decision_counters

            if self.config.metrics_redis_enabled:
                record_decision_counters(self.config.redis_url, branch="skip_path", allowed=True)
            if self.config.structured_decision_logging:
                from django_ip_safeguard.services.structured_decision_log import log_structured_decision

                log_structured_decision(
                    policy_name="",
                    branch="skip_path",
                    allowed=True,
                    path=request.path,
                    method=request.method,
                    ip_masked="",
                )
        except Exception:  # noqa: BLE001
            pass

    def _record_observation(self, request, cfg, *, client_ip: str, branch: str, allowed: bool, action=None):
        """Redis 计数 + 可选单行 JSON 日志。"""
        policy_name = getattr(cfg, "policy_name", None) or "default"
        if cfg.metrics_redis_enabled:
            try:
                from django_ip_safeguard.services.decision_metrics import record_decision_counters

                record_decision_counters(
                    cfg.redis_url,
                    policy_name=policy_name,
                    branch=branch,
                    allowed=allowed,
                    action=action,
                )
            except Exception:  # noqa: BLE001
                pass
        if cfg.structured_decision_logging:
            try:
                from django_ip_safeguard.services.structured_decision_log import log_structured_decision

                ip_disp = mask_ip(client_ip, cfg.ip_mask_enabled, cfg.ip_mask_keep_prefix) if client_ip else ""
                log_structured_decision(
                    policy_name=policy_name,
                    branch=branch,
                    allowed=allowed,
                    action=action,
                    path=request.path,
                    method=request.method,
                    ip_masked=ip_disp,
                )
            except Exception:  # noqa: BLE001
                pass

    def __call__(self, request):
        # 跳过路径：在策略加载之前就返回，能力上等同"未启用"
        skip_prefixes = tuple(self.config.skip_path_prefixes or ())
        if skip_prefixes and _path_in(skip_prefixes, request.path):
            self._record_skip_path(request)
            return self.get_response(request)

        runtime_config = load_effective_policy(self.config, request=request)

        if not runtime_config.enabled:
            self._record_observation(request, runtime_config, client_ip="", branch="disabled", allowed=True)
            return self.get_response(request)

        client_ip = resolve_client_ip(request, runtime_config.trusted_proxy_cidrs)
        if not client_ip:
            self._record_observation(request, runtime_config, client_ip="", branch="no_client_ip", allowed=True)
            return self.get_response(request)

        wl_hit, _wl_rule = first_matching_rule(client_ip, runtime_config.ip_whitelist)
        if wl_hit:
            self._record_observation(request, runtime_config, client_ip=client_ip, branch="whitelist", allowed=True)
            return self.get_response(request)

        policy_intel = IpIntel(ip=client_ip, country_code="", risk_score=0, risk_tags=[], source="policy")

        bl_hit, bl_rule = first_matching_rule(client_ip, runtime_config.ip_blacklist)
        if bl_hit:
            reason = _t("命中 IP 黑名单: %(rule)s") % {"rule": bl_rule}
            log_access_decision(
                enabled=runtime_config.use_db_log,
                ip=client_ip,
                path=request.path,
                decision="block",
                reason=reason,
                ip_intel=policy_intel,
                ip_mask_enabled=runtime_config.ip_mask_enabled,
                ip_mask_keep_prefix=runtime_config.ip_mask_keep_prefix,
                **_audit_request_meta(request),
            )
            self._record_observation(request, runtime_config, client_ip=client_ip, branch="blacklist", allowed=False)
            return self._build_block(request, runtime_config, ip=client_ip, reason=str(reason))

        geo_reason = evaluate_geo_ip_pool_rules(client_ip, runtime_config, self.cache_service)
        if geo_reason:
            log_access_decision(
                enabled=runtime_config.use_db_log,
                ip=client_ip,
                path=request.path,
                decision="block",
                reason=geo_reason,
                ip_intel=policy_intel,
                ip_mask_enabled=runtime_config.ip_mask_enabled,
                ip_mask_keep_prefix=runtime_config.ip_mask_keep_prefix,
                **_audit_request_meta(request),
            )
            self._record_observation(request, runtime_config, client_ip=client_ip, branch="geo_pool", allowed=False)
            return self._build_block(request, runtime_config, ip=client_ip, reason=geo_reason)

        if self._is_rate_limited(client_ip, runtime_config.rate_limit_per_minute):
            reason = str(_t("超过单 IP 每分钟请求上限"))
            log_access_decision(
                enabled=runtime_config.use_db_log,
                ip=client_ip,
                path=request.path,
                decision="block",
                reason=reason,
                ip_intel=policy_intel,
                ip_mask_enabled=runtime_config.ip_mask_enabled,
                ip_mask_keep_prefix=runtime_config.ip_mask_keep_prefix,
                **_audit_request_meta(request),
            )
            self._record_observation(request, runtime_config, client_ip=client_ip, branch="ratelimit", allowed=False)
            return self._build_block(request, runtime_config, ip=client_ip, reason=reason, action="rate_limit")

        if self._is_banned(client_ip):
            reason = str(_t("IP 已被封禁"))
            log_access_decision(
                enabled=runtime_config.use_db_log,
                ip=client_ip,
                path=request.path,
                decision="block",
                reason=reason,
                ip_intel=policy_intel,
                ip_mask_enabled=runtime_config.ip_mask_enabled,
                ip_mask_keep_prefix=runtime_config.ip_mask_keep_prefix,
                **_audit_request_meta(request),
            )
            self._record_observation(request, runtime_config, client_ip=client_ip, branch="banned", allowed=False)
            return self._build_block(request, runtime_config, ip=client_ip, reason=reason)

        ip_intel = self._get_intel_from_cache(client_ip)
        if not ip_intel:
            if not self.circuit_breaker.allow_request():
                logger.warning("Provider 熔断生效，跳过外部请求。")
                return self._handle_provider_failed(request, runtime_config, client_ip)

            lock_acquired = self._acquire_lock(
                client_ip, ttl=runtime_config.dedupe_lock_seconds
            )
            if not lock_acquired:
                # 短暂等待，给持锁的另一进程留出写缓存的时间，再尝试读取一次
                time.sleep(0.05)
                ip_intel = self._get_intel_from_cache(client_ip)
                if not ip_intel:
                    return self._handle_provider_failed(request, runtime_config, client_ip)
            else:
                try:
                    ip_intel = self.provider.fetch_ip_intel(client_ip)
                    self.asn_lookup.enrich_ip_intel(ip_intel)

                    if not ip_intel.country_code or ip_intel.country_code.upper() == "UNKNOWN":
                        inferred = infer_country_from_pools(client_ip, self.config, self.cache_service)
                        if inferred:
                            ip_intel.country_code = inferred
                            if inferred == "CN" and not ip_intel.country_name:
                                ip_intel.country_name = "中国"

                    if self.local_risk_engine:
                        local_reasons = self.local_risk_engine.evaluate(client_ip, ip_intel)
                        if local_reasons:
                            logger.info("本地风险规则命中: %s - %s", client_ip, local_reasons)

                    ttl = (
                        runtime_config.high_risk_cache_ttl
                        if ip_intel.risk_score >= runtime_config.risk_score_threshold
                        else runtime_config.low_risk_cache_ttl
                    )
                    self._set_intel_to_cache(ip_intel, ttl=ttl)
                    self.circuit_breaker.record_success()
                except Exception as exc:
                    logger.exception("IP 情报查询失败: %s", exc)
                    self.circuit_breaker.record_failure()
                    return self._handle_provider_failed(request, runtime_config, client_ip)
                finally:
                    self._release_lock(client_ip)

        decision = evaluate_ip_risk(ip_intel, runtime_config)
        if not decision.allow:
            log_access_decision(
                enabled=runtime_config.use_db_log,
                ip=client_ip,
                path=request.path,
                decision="block",
                reason=decision.reason,
                ip_intel=ip_intel,
                ip_mask_enabled=runtime_config.ip_mask_enabled,
                ip_mask_keep_prefix=runtime_config.ip_mask_keep_prefix,
                **_audit_request_meta(request),
            )
            if decision.should_ban:
                ban_ip(
                    cache_service=self.cache_service,
                    ip=client_ip,
                    reason=decision.reason,
                    ban_ttl=decision.ban_ttl or runtime_config.ban_ttl,
                )
            if self.ip_correlation:
                self.ip_correlation.record_access(client_ip, is_blocked=True)
            risk_action = decision.action if decision.action in {"block", "ban", "challenge", "rate_limit"} else "block"
            self._record_observation(
                request,
                runtime_config,
                client_ip=client_ip,
                branch="risk",
                allowed=False,
                action=risk_action,
            )
            return self._build_block(
                request, runtime_config, ip=client_ip, reason=decision.reason, action=risk_action
            )

        log_access_decision(
            enabled=runtime_config.use_db_log,
            ip=client_ip,
            path=request.path,
            decision="allow",
            reason=decision.reason,
            ip_intel=ip_intel,
            ip_mask_enabled=runtime_config.ip_mask_enabled,
            ip_mask_keep_prefix=runtime_config.ip_mask_keep_prefix,
            **_audit_request_meta(request),
        )
        self._record_observation(request, runtime_config, client_ip=client_ip, branch="risk", allowed=True)
        if self.ip_correlation:
            self.ip_correlation.record_access(client_ip, is_blocked=False)
        return self.get_response(request)

    def _handle_provider_failed(self, request, runtime_config, client_ip: str = ""):
        fail_open_now = should_fail_open(
            path=request.path,
            default_fail_open=runtime_config.fail_open,
            open_prefixes=runtime_config.fail_open_path_prefixes,
            close_prefixes=runtime_config.fail_close_path_prefixes,
        )
        if fail_open_now:
            self._record_observation(
                request, runtime_config, client_ip=client_ip, branch="intel_fail_open", allowed=True
            )
            return self.get_response(request)
        self._record_observation(
            request, runtime_config, client_ip=client_ip, branch="intel_fail_close", allowed=False
        )
        return JsonResponse(
            {"detail": str(_t("IP 风险服务暂不可用"))},
            status=runtime_config.block_status_code,
        )
