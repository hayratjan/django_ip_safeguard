import logging

from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _

from django_ip_safeguard.conf import get_settings
from django_ip_safeguard.services.audit_service import log_access_decision
from django_ip_safeguard.services.ban_service import ban_ip
from django_ip_safeguard.services.cache import RedisCacheService
from django_ip_safeguard.services.circuit_breaker import CircuitBreaker
from django_ip_safeguard.services.ip_matcher import first_matching_rule
from django_ip_safeguard.services.ip_resolver import resolve_client_ip
from django_ip_safeguard.services.layered_cache import LayeredCacheService
from django_ip_safeguard.services.provider_factory import build_provider
from django_ip_safeguard.services.geo_ip_pool_runtime import evaluate_geo_ip_pool_rules
from django_ip_safeguard.services.policy_service import load_effective_policy
from django_ip_safeguard.services.risk_engine import evaluate_ip_risk
from django_ip_safeguard.services.asn_lookup import AsnLookupService
from django_ip_safeguard.types import IpIntel

logger = logging.getLogger(__name__)


def should_fail_open(path: str, default_fail_open: bool, open_prefixes: tuple, close_prefixes: tuple) -> bool:
    for prefix in close_prefixes:
        if prefix and path.startswith(prefix):
            return False
    for prefix in open_prefixes:
        if prefix and path.startswith(prefix):
            return True
    return default_fail_open


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

    def __call__(self, request):
        runtime_config = load_effective_policy(self.config)

        if not runtime_config.enabled:
            return self.get_response(request)

        client_ip = resolve_client_ip(request, runtime_config.trusted_proxy_cidrs)
        if not client_ip:
            return self.get_response(request)

        wl_hit, _ = first_matching_rule(client_ip, runtime_config.ip_whitelist)
        if wl_hit:
            return self.get_response(request)

        policy_intel = IpIntel(ip=client_ip, country_code="", risk_score=0, risk_tags=[], source="policy")

        bl_hit, bl_rule = first_matching_rule(client_ip, runtime_config.ip_blacklist)
        if bl_hit:
            reason = _("命中 IP 黑名单: %(rule)s") % {"rule": bl_rule}
            log_access_decision(
                enabled=runtime_config.use_db_log,
                ip=client_ip,
                path=request.path,
                decision="block",
                reason=reason,
                ip_intel=policy_intel,
                ip_mask_enabled=runtime_config.ip_mask_enabled,
                ip_mask_keep_prefix=runtime_config.ip_mask_keep_prefix,
            )
            return JsonResponse(
                {
                    "detail": str(_("访问被安全策略阻止")),
                    "reason": str(reason),
                    "ip": client_ip,
                },
                status=runtime_config.block_status_code,
            )

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
            )
            return JsonResponse(
                {
                    "detail": str(_("访问被安全策略阻止")),
                    "reason": geo_reason,
                    "ip": client_ip,
                },
                status=runtime_config.block_status_code,
            )

        if self._is_rate_limited(client_ip, runtime_config.rate_limit_per_minute):
            reason = str(_("超过单 IP 每分钟请求上限"))
            log_access_decision(
                enabled=runtime_config.use_db_log,
                ip=client_ip,
                path=request.path,
                decision="block",
                reason=reason,
                ip_intel=policy_intel,
                ip_mask_enabled=runtime_config.ip_mask_enabled,
                ip_mask_keep_prefix=runtime_config.ip_mask_keep_prefix,
            )
            return JsonResponse(
                {
                    "detail": str(_("访问被安全策略阻止")),
                    "reason": reason,
                    "ip": client_ip,
                },
                status=runtime_config.block_status_code,
            )

        if self._is_banned(client_ip):
            return JsonResponse(
                {"detail": str(_("IP 已被封禁")), "ip": client_ip},
                status=runtime_config.block_status_code,
            )

        ip_intel = self._get_intel_from_cache(client_ip)
        if not ip_intel:
            if not self.circuit_breaker.allow_request():
                logger.warning("Provider 熔断生效，跳过外部请求。")
                return self._handle_provider_failed(request, runtime_config)

            lock_acquired = self._acquire_lock(
                client_ip, ttl=runtime_config.dedupe_lock_seconds
            )
            if not lock_acquired:
                return self._handle_provider_failed(request, runtime_config)
            try:
                ip_intel = self.provider.fetch_ip_intel(client_ip)
                self.asn_lookup.enrich_ip_intel(ip_intel)

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
                return self._handle_provider_failed(request, runtime_config)
            finally:
                if lock_acquired:
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
            return JsonResponse(
                {"detail": str(_("访问被安全策略阻止")), "reason": decision.reason, "ip": client_ip},
                status=runtime_config.block_status_code,
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
        )
        if self.ip_correlation:
            self.ip_correlation.record_access(client_ip, is_blocked=False)
        return self.get_response(request)

    def _handle_provider_failed(self, request, runtime_config):
        fail_open_now = should_fail_open(
            path=request.path,
            default_fail_open=runtime_config.fail_open,
            open_prefixes=runtime_config.fail_open_path_prefixes,
            close_prefixes=runtime_config.fail_close_path_prefixes,
        )
        if fail_open_now:
            return self.get_response(request)
        return JsonResponse(
            {"detail": str(_("IP 风险服务暂不可用"))},
            status=runtime_config.block_status_code,
        )
