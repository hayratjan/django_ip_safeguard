import logging
from typing import Dict, Optional, Set

from django_ip_safeguard.types import IpIntel

logger = logging.getLogger(__name__)

KNOWN_DATACENTER_ASNS: Dict[int, str] = {
    13335: "Cloudflare",
    14618: "Amazon AWS",
    16509: "Amazon AWS",
    8075: "Microsoft Azure",
    13414: "Twitter",
    26496: "GoDaddy",
    20446: "Highwinds",
    63949: "Linode",
    45090: "Tencent Cloud",
    37963: "Alibaba Cloud",
    38365: "Baidu Cloud",
    55990: "Huawei Cloud",
    58519: "Alibaba Cloud (CN)",
    55933: "Tencent Cloud (CN)",
    45102: "Alibaba Cloud (INTL)",
    8068: "Huawei Cloud",
    36351: "SoftLayer",
    53824: "Vultr",
    62041: "DigitalOcean",
    14061: "DigitalOcean",
    20473: "Vultr",
    63927: "OVH Singapore",
    16276: "OVH SAS",
    24940: "Hetzner",
    213230: "Hetzner Online",
    60781: "Leaseweb",
    62567: "DigitalOcean (2)",
    46606: "Unified Layer",
    32475: "SingleHop",
    36352: "Hostwinds",
    53667: "FranTech",
    53345: "ServerMania",
    30637: "Leaseweb USA",
    23470: "Ping An Cloud",
    55723: "UCloud",
    64900: "QingCloud",
}

KNOWN_CDN_ASNS: Dict[int, str] = {
    13335: "Cloudflare CDN",
    15169: "Google CDN",
    16509: "CloudFront CDN",
    54113: "Fastly",
    20940: "Akamai",
    16625: "Akamai (2)",
    12222: "Akamai (3)",
    45090: "Tencent CDN",
    38365: "Baidu CDN",
    55933: "Tencent CDN (2)",
}


class AsnLookupService:
    """ASN 查询服务：基于本地 ASN 数据库或 GeoIP2 ASN 数据。"""

    def __init__(self):
        self._datacenter_asns: Set[int] = set(KNOWN_DATACENTER_ASNS.keys())
        self._cdn_asns: Set[int] = set(KNOWN_CDN_ASNS.keys())

    def enrich_ip_intel(self, ip_intel: IpIntel) -> None:
        if ip_intel.asn is None:
            return

        if ip_intel.asn in self._datacenter_asns:
            ip_intel.is_datacenter = True
            if not ip_intel.asn_org:
                ip_intel.asn_org = KNOWN_DATACENTER_ASNS.get(ip_intel.asn, "")

        if ip_intel.asn in self._cdn_asns and "cdn" not in ip_intel.risk_tags:
            ip_intel.risk_tags.append("cdn")

    def is_datacenter(self, asn: Optional[int]) -> bool:
        if asn is None:
            return False
        return asn in self._datacenter_asns

    def is_cdn(self, asn: Optional[int]) -> bool:
        if asn is None:
            return False
        return asn in self._cdn_asns

    def get_org_name(self, asn: Optional[int]) -> str:
        if asn is None:
            return ""
        return KNOWN_DATACENTER_ASNS.get(asn, KNOWN_CDN_ASNS.get(asn, ""))

    def get_all_datacenter_asns(self) -> Dict[int, str]:
        return dict(KNOWN_DATACENTER_ASNS)

    def get_all_cdn_asns(self) -> Dict[int, str]:
        return dict(KNOWN_CDN_ASNS)
