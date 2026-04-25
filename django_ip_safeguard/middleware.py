import logging

from django.http import JsonResponse

from django_ip_safeguard.conf import get_settings
from django_ip_safeguard.services.audit_service import log_access_decision
from django_ip_safeguard.services.ban_service import ban_ip
from django_ip_safeguard.services.cache import RedisCacheService
from django_ip_safeguard.services.ip_resolver import resolve_client_ip
from django_ip_safeguard.services.provider_factory import build_provider
from django_ip_safeguard.services.risk_engine import evaluate_ip_risk

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

    def __call__(self, request):
        if not self.config.enabled:
            return self.get_response(request)

        client_ip = resolve_client_ip(request, self.config.trusted_proxy_cidrs)
        if not client_ip:
            return self.get_response(request)

        if self.cache_service.is_banned(client_ip):
            return JsonResponse(
                {"detail": "IP 已被封禁", "ip": client_ip},
                status=self.config.block_status_code,
            )

        ip_intel = self.cache_service.get_ip_intel(client_ip)
        if not ip_intel:
            try:
                ip_intel = self.provider.fetch_ip_intel(client_ip)
                self.cache_service.set_ip_intel(ip_intel, ttl=self.config.cache_ttl)
            except Exception as exc:  # noqa: BLE001
                logger.exception("IP 情报查询失败: %s", exc)
                fail_open_now = should_fail_open(
                    path=request.path,
                    default_fail_open=self.config.fail_open,
                    open_prefixes=self.config.fail_open_path_prefixes,
                    close_prefixes=self.config.fail_close_path_prefixes,
                )
                if fail_open_now:
                    return self.get_response(request)
                return JsonResponse(
                    {"detail": "IP 风险服务暂不可用"},
                    status=self.config.block_status_code,
                )

        decision = evaluate_ip_risk(ip_intel, self.config)
        if not decision.allow:
            log_access_decision(
                enabled=self.config.use_db_log,
                ip=client_ip,
                path=request.path,
                decision="block",
                reason=decision.reason,
                ip_intel=ip_intel,
            )
            if decision.should_ban:
                ban_ip(
                    cache_service=self.cache_service,
                    ip=client_ip,
                    reason=decision.reason,
                    ban_ttl=decision.ban_ttl or self.config.ban_ttl,
                )
            return JsonResponse(
                {"detail": "访问被安全策略阻止", "reason": decision.reason, "ip": client_ip},
                status=self.config.block_status_code,
            )

        log_access_decision(
            enabled=self.config.use_db_log,
            ip=client_ip,
            path=request.path,
            decision="allow",
            reason=decision.reason,
            ip_intel=ip_intel,
        )
        return self.get_response(request)
