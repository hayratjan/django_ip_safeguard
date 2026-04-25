import logging

from django.http import JsonResponse

from django_ip_safeguard.conf import get_settings
from django_ip_safeguard.services.audit_service import log_access_decision
from django_ip_safeguard.services.ban_service import ban_ip
from django_ip_safeguard.services.cache import RedisCacheService
from django_ip_safeguard.services.circuit_breaker import CircuitBreaker
from django_ip_safeguard.services.ip_matcher import first_matching_rule
from django_ip_safeguard.services.ip_resolver import resolve_client_ip
from django_ip_safeguard.services.provider_factory import build_provider
from django_ip_safeguard.services.geo_ip_pool_runtime import evaluate_geo_ip_pool_rules
from django_ip_safeguard.services.policy_service import load_effective_policy
from django_ip_safeguard.services.risk_engine import evaluate_ip_risk
from django_ip_safeguard.types import IpIntel

logger = logging.getLogger(__name__)


def should_fail_open(path: str, default_fail_open: bool, open_prefixes: tuple, close_prefixes: tuple) -> bool:
    """按路径前缀决定外部服务失败时是否放行。"""

    for prefix in close_prefixes:
        if prefix and path.startswith(prefix):
            return False
    for prefix in open_prefixes:
        if prefix and path.startswith(prefix):
            return True
    return default_fail_open


class IpGuardMiddleware:
    """IP 安全中间件。"""

    def __init__(self, get_response):
        self.get_response = get_response
        self.config = get_settings()
        self.cache_service = RedisCacheService(self.config.redis_url)
        self.provider = build_provider(self.config)
        self.circuit_breaker = CircuitBreaker(
            cache_service=self.cache_service,
            failure_threshold=self.config.provider_circuit_breaker_failures,
            recovery_timeout=self.config.provider_circuit_breaker_ttl,
        )

    def __call__(self, request):
        runtime_config = load_effective_policy(self.config)

        if not runtime_config.enabled:
            return self.get_response(request)

        client_ip = resolve_client_ip(request, runtime_config.trusted_proxy_cidrs)
        if not client_ip:
            return self.get_response(request)

        # 策略 IP：白名单优先（支持单 IP / CIDR），命中则跳过黑名单、限流与情报
        wl_hit, _ = first_matching_rule(client_ip, runtime_config.ip_whitelist)
        if wl_hit:
            return self.get_response(request)

        policy_intel = IpIntel(ip=client_ip, country_code="", risk_score=0, risk_tags=[], source="policy")

        bl_hit, bl_rule = first_matching_rule(client_ip, runtime_config.ip_blacklist)
        if bl_hit:
            log_access_decision(
                enabled=runtime_config.use_db_log,
                ip=client_ip,
                path=request.path,
                decision="block",
                reason=f"命中 IP 黑名单: {bl_rule}",
                ip_intel=policy_intel,
                ip_mask_enabled=runtime_config.ip_mask_enabled,
                ip_mask_keep_prefix=runtime_config.ip_mask_keep_prefix,
            )
            return JsonResponse(
                {
                    "detail": "访问被安全策略阻止",
                    "reason": f"命中 IP 黑名单: {bl_rule}",
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
                    "detail": "访问被安全策略阻止",
                    "reason": geo_reason,
                    "ip": client_ip,
                },
                status=runtime_config.block_status_code,
            )

        if self.cache_service.is_rate_limited(client_ip, runtime_config.rate_limit_per_minute):
            log_access_decision(
                enabled=runtime_config.use_db_log,
                ip=client_ip,
                path=request.path,
                decision="block",
                reason="超过单 IP 每分钟请求上限",
                ip_intel=policy_intel,
                ip_mask_enabled=runtime_config.ip_mask_enabled,
                ip_mask_keep_prefix=runtime_config.ip_mask_keep_prefix,
            )
            return JsonResponse(
                {
                    "detail": "访问被安全策略阻止",
                    "reason": "超过单 IP 每分钟请求上限",
                    "ip": client_ip,
                },
                status=runtime_config.block_status_code,
            )

        if self.cache_service.is_banned(client_ip):
            return JsonResponse(
                {"detail": "IP 已被封禁", "ip": client_ip},
                status=runtime_config.block_status_code,
            )

        ip_intel = self.cache_service.get_ip_intel(client_ip)
        if not ip_intel:
            if not self.circuit_breaker.allow_request():
                logger.warning("Provider 熔断生效，跳过外部请求。")
                return self._handle_provider_failed(request, runtime_config)

            lock_acquired = self.cache_service.acquire_intel_lock(
                client_ip, ttl=runtime_config.dedupe_lock_seconds
            )
            if not lock_acquired:
                # 并发请求场景下其他请求正在查询，优先降级避免击穿。
                return self._handle_provider_failed(request, runtime_config)
            try:
                ip_intel = self.provider.fetch_ip_intel(client_ip)
                ttl = (
                    runtime_config.high_risk_cache_ttl
                    if ip_intel.risk_score >= runtime_config.risk_score_threshold
                    else runtime_config.low_risk_cache_ttl
                )
                self.cache_service.set_ip_intel(ip_intel, ttl=ttl)
                self.circuit_breaker.record_success()
            except Exception as exc:  # noqa: BLE001
                logger.exception("IP 情报查询失败: %s", exc)
                self.circuit_breaker.record_failure()
                return self._handle_provider_failed(request, runtime_config)
            finally:
                if lock_acquired:
                    self.cache_service.release_intel_lock(client_ip)

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
            return JsonResponse(
                {"detail": "访问被安全策略阻止", "reason": decision.reason, "ip": client_ip},
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
            {"detail": "IP 风险服务暂不可用"},
            status=runtime_config.block_status_code,
        )


