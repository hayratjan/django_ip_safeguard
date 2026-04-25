from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class IpIntel:
    """IP 情报数据结构。"""

    ip: str
    country_code: Optional[str] = None
    country_name: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    asn: Optional[int] = None
    asn_org: Optional[str] = None
    is_datacenter: bool = False
    is_proxy: bool = False
    is_vpn: bool = False
    is_tor: bool = False
    is_botnet: bool = False
    risk_score: int = 0
    risk_tags: List[str] = field(default_factory=list)
    source: str = "unknown"


@dataclass
class RiskDecision:
    """风险判定结果。"""

    allow: bool
    reason: str
    should_ban: bool = False
    ban_ttl: Optional[int] = None
    local_risk_reasons: List[str] = field(default_factory=list)


@dataclass
class ThreatIntelEntry:
    """威胁情报条目。"""

    ip_or_cidr: str
    threat_type: str
    source: str
    confidence: int = 0
    description: str = ""
    auto_ban: bool = False
    ttl: int = 86400


@dataclass
class SubnetCorrelation:
    """子网关联分析结果。"""

    subnet: str
    total_ips: int
    blocked_ips: int
    attack_ratio: float
    correlated_ips: List[str] = field(default_factory=list)
