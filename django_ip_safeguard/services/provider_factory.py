from django_ip_safeguard.conf import IpGuardSettings
from django_ip_safeguard.services.provider_base import BaseIpIntelProvider
from django_ip_safeguard.services.provider_chain import ChainedProvider
from django_ip_safeguard.services.provider_http import DummyIpIntelProvider, HttpIpIntelProvider


def _build_geoip2_provider(cfg: IpGuardSettings) -> BaseIpIntelProvider:
    from django_ip_safeguard.services.provider_geoip2 import GeoIP2LocalProvider
    return GeoIP2LocalProvider(
        city_db_path=cfg.geoip2_city_db_path,
        asn_db_path=cfg.geoip2_asn_db_path,
    )


def _build_single_provider(name: str, cfg: IpGuardSettings) -> BaseIpIntelProvider:
    provider_name = name.lower()
    if provider_name == "dummy":
        return DummyIpIntelProvider()
    if provider_name == "http":
        return HttpIpIntelProvider(
            endpoint=cfg.provider_endpoint,
            api_key=cfg.provider_api_key,
            timeout=cfg.provider_timeout,
            max_retries=cfg.provider_max_retries,
            retry_backoff=cfg.provider_retry_backoff,
            headers=dict(cfg.provider_headers),
        )
    if provider_name == "geoip2":
        return _build_geoip2_provider(cfg)
    raise ValueError(f"不支持的 IP Provider: {name}")


def build_provider(config: IpGuardSettings) -> BaseIpIntelProvider:
    """根据配置构建 Provider，支持降级链模式。"""

    if config.provider_chain_enabled and config.provider_chain_names:
        providers = []
        for name in config.provider_chain_names:
            try:
                providers.append(_build_single_provider(name, config))
            except ValueError:
                continue
        if providers:
            return ChainedProvider(providers, merge_results=True)

    if config.geoip2_enabled:
        providers = [_build_single_provider(config.provider, config)]
        providers.append(_build_geoip2_provider(config))
        return ChainedProvider(providers, merge_results=True)

    return _build_single_provider(config.provider, config)
