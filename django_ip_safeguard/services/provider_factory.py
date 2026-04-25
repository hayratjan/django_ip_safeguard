from django_ip_safeguard.conf import IpGuardSettings
from django_ip_safeguard.services.provider_base import BaseIpIntelProvider
from django_ip_safeguard.services.provider_http import DummyIpIntelProvider, HttpIpIntelProvider


def build_provider(config: IpGuardSettings) -> BaseIpIntelProvider:
    """根据配置构建 Provider。"""

    provider_name = (config.provider or "dummy").lower()
    if provider_name == "dummy":
        return DummyIpIntelProvider()
    if provider_name == "http":
        return HttpIpIntelProvider(
            endpoint=config.provider_endpoint,
            api_key=config.provider_api_key,
            timeout=config.provider_timeout,
            max_retries=config.provider_max_retries,
            retry_backoff=config.provider_retry_backoff,
            headers=dict(config.provider_headers),
        )
    raise ValueError(f"不支持的 IP Provider: {config.provider}")
