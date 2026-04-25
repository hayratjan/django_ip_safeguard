from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class IpIntel:
    """IP 情报数据结构。"""

    ip: str
    country_code: Optional[str] = None
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
