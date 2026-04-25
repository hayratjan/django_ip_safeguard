import logging
from typing import List

from django_ip_safeguard.services.provider_base import BaseIpIntelProvider
from django_ip_safeguard.types import IpIntel

logger = logging.getLogger(__name__)


class ChainedProvider(BaseIpIntelProvider):
    """
    多 Provider 降级链：依次尝试每个 Provider，任一成功即返回。
    合并多个来源的情报数据，优先使用第一个成功的结果，
    后续 Provider 补充前者缺失的字段。
    """

    def __init__(self, providers: List[BaseIpIntelProvider], merge_results: bool = True):
        self.providers = providers
        self.merge_results = merge_results

    def fetch_ip_intel(self, ip: str) -> IpIntel:
        if not self.providers:
            return IpIntel(ip=ip, source="empty_chain")

        if not self.merge_results:
            return self._first_success(ip)

        return self._merge_all(ip)

    def _first_success(self, ip: str) -> IpIntel:
        for provider in self.providers:
            try:
                result = provider.fetch_ip_intel(ip)
                if result.country_code and result.country_code != "UNKNOWN":
                    return result
            except Exception as exc:
                provider_name = type(provider).__name__
                logger.debug("Provider %s 查询失败: %s", provider_name, exc)
                continue
        return IpIntel(ip=ip, source="chain_fallback")

    def _merge_all(self, ip: str) -> IpIntel:
        merged = IpIntel(ip=ip, source="chain_merged")
        sources = []

        for provider in self.providers:
            try:
                result = provider.fetch_ip_intel(ip)
                sources.append(result.source)
                self._merge_into(merged, result)
            except Exception as exc:
                provider_name = type(provider).__name__
                logger.debug("Provider %s 查询失败: %s", provider_name, exc)
                continue

        if sources:
            merged.source = "+".join(sources)
        return merged

    @staticmethod
    def _merge_into(target: IpIntel, source: IpIntel) -> None:
        if source.country_code and (not target.country_code or target.country_code == "UNKNOWN"):
            target.country_code = source.country_code
        if source.country_name and not target.country_name:
            target.country_name = source.country_name
        if source.region and not target.region:
            target.region = source.region
        if source.city and not target.city:
            target.city = source.city
        if source.latitude is not None and target.latitude is None:
            target.latitude = source.latitude
        if source.longitude is not None and target.longitude is None:
            target.longitude = source.longitude
        if source.asn is not None and target.asn is None:
            target.asn = source.asn
        if source.asn_org and not target.asn_org:
            target.asn_org = source.asn_org
        if source.is_datacenter:
            target.is_datacenter = True
        if source.is_proxy:
            target.is_proxy = True
        if source.is_vpn:
            target.is_vpn = True
        if source.is_tor:
            target.is_tor = True
        if source.is_botnet:
            target.is_botnet = True
        if source.risk_score > target.risk_score:
            target.risk_score = source.risk_score
        existing = set(target.risk_tags)
        for tag in source.risk_tags:
            if tag not in existing:
                target.risk_tags.append(tag)
                existing.add(tag)
