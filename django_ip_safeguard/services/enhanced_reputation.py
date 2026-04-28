import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from django_ip_safeguard.conf import IpGuardSettings
from django_ip_safeguard.services.cache import RedisCacheService
from django_ip_safeguard.types import IpIntel

logger = logging.getLogger(__name__)


@dataclass
class RiskFactor:
    name: str
    weight: float
    base_score: int
    description: str


@dataclass
class IpReputationProfile:
    ip: str
    total_requests: int = 0
    blocked_requests: int = 0
    allowed_requests: int = 0
    avg_risk_score: float = 0.0
    threat_types: List[str] = field(default_factory=list)
    countries: List[str] = field(default_factory=list)
    first_seen: str = ""
    last_seen: str = ""
    consecutive_high_risk: int = 0
    consecutive_normal: int = 0
    asn_reputation: float = 0.0
    country_reputation: float = 0.0
    behavioral_score: float = 0.0
    final_reputation_score: float = 0.0


RISK_FACTORS = {
    "tor_exit": RiskFactor("Tor出口节点", weight=1.5, base_score=20, description="通过Tor网络访问"),
    "botnet": RiskFactor("僵尸网络", weight=1.8, base_score=25, description="属于已知僵尸网络"),
    "proxy_vpn": RiskFactor("代理/VPN", weight=1.2, base_score=15, description="使用代理或VPN"),
    "datacenter": RiskFactor("数据中心", weight=0.3, base_score=5, description="来自数据中心/IDC"),
    "spamhaus_drop": RiskFactor("Spamhaus DROP", weight=1.6, base_score=20, description="出现在Spamhaus黑名单"),
    "emerging_threats": RiskFactor("Emerging Threats", weight=1.4, base_score=18, description="出现在Emerging Threats黑名单"),
    "subnet_attack": RiskFactor("同段攻击", weight=1.3, base_score=15, description="同C段存在攻击行为"),
    "abuse_confidence": RiskFactor("AbuseIPDB", weight=1.2, base_score=20, description="AbuseIPDB举报置信度"),
    "country_blocked": RiskFactor("国家封锁", weight=1.4, base_score=25, description="来自被封锁国家"),
    "asn_malicious": RiskFactor("ASN恶意", weight=1.3, base_score=20, description="ASN存在恶意行为"),
    "rate_exceeded": RiskFactor("速率超标", weight=1.1, base_score=15, description="请求频率超过限制"),
    "rapid_fire": RiskFactor("快读攻击", weight=1.5, base_score=20, description="短时间内大量请求"),
}


class EnhancedIpReputationScorer:
    """
    增强版IP信誉评分服务：
    - 多维度风险因子加权评分
    - 历史行为分析
    - ASN/国家信誉库
    - 动态风险等级调整
    """

    def __init__(self, cache_service: RedisCacheService, config: IpGuardSettings):
        self.cache = cache_service
        self.config = config
        self._profile_cache_ttl = 1800
        self._country_reputation_db = self._load_country_reputation_db()
        self._asn_reputation_db = self._load_asn_reputation_db()

    def calculate_reputation_score(self, ip: str, ip_intel: IpIntel, context: Optional[Dict[str, Any]] = None) -> Tuple[float, List[str]]:
        """
        计算IP信誉评分，返回 (信誉分数, 风险因子列表)
        信誉分数范围 0-100，数值越低表示越可信
        """
        factors = []
        total_weighted_score = 0.0
        total_weight = 0.0

        factor_scores = self._evaluate_risk_factors(ip, ip_intel, context)
        for factor_name, (base_score, details) in factor_scores.items():
            if factor_name in RISK_FACTORS:
                factor = RISK_FACTORS[factor_name]
                weighted = base_score * factor.weight
                total_weighted_score += weighted
                total_weight += factor.weight
                if base_score > 0:
                    factors.append(f"{factor.description}: +{base_score}(权重:{factor.weight})")

        if total_weight > 0:
            final_score = min(100, total_weighted_score / total_weight)
        else:
            final_score = 0.0

        profile = self._get_ip_profile(ip)
        if profile:
            behavioral_adjustment = self._calculate_behavioral_adjustment(profile)
            final_score = min(100, final_score + behavioral_adjustment)
            if behavioral_adjustment != 0:
                factors.append(f"行为调整: {'+' if behavioral_adjustment > 0 else ''}{behavioral_adjustment:.1f}")

        final_score = max(0, min(100, final_score))
        return round(final_score, 2), factors

    def _evaluate_risk_factors(
        self, ip: str, ip_intel: IpIntel, context: Optional[Dict[str, Any]]
    ) -> Dict[str, Tuple[int, str]]:
        scores = {}

        if ip_intel.is_tor:
            scores["tor_exit"] = (RISK_FACTORS["tor_exit"].base_score, "Tor出口节点")

        if ip_intel.is_botnet:
            scores["botnet"] = (RISK_FACTORS["botnet"].base_score, "僵尸网络")

        if ip_intel.is_proxy or ip_intel.is_vpn:
            scores["proxy_vpn"] = (RISK_FACTORS["proxy_vpn"].base_score, "代理/VPN")

        if ip_intel.is_datacenter:
            scores["datacenter"] = (RISK_FACTORS["datacenter"].base_score, "数据中心")

        if "subnet_attack" in ip_intel.risk_tags:
            scores["subnet_attack"] = (RISK_FACTORS["subnet_attack"].base_score, "同段攻击")

        country = ip_intel.country_code or (context.get("country_code") if context else None)
        if country and country in self._country_reputation_db:
            rep = self._country_reputation_db[country]
            if rep < 0.3:
                scores["country_blocked"] = (
                    int(20 * (0.3 - rep) / 0.3),
                    f"低信誉国家: {country}"
                )

        if ip_intel.asn and ip_intel.asn in self._asn_reputation_db:
            asn_rep = self._asn_reputation_db[ip_intel.asn]
            if asn_rep < 0.3:
                scores["asn_malicious"] = (
                    int(20 * (0.3 - asn_rep) / 0.3),
                    f"低信誉ASN: {ip_intel.asn}"
                )

        threat_types = set()
        for tag in ip_intel.risk_tags:
            if tag in ("spamhaus", "drop"):
                threat_types.add("spamhaus_drop")
            elif tag in ("emerging", "malware"):
                threat_types.add("emerging_threats")

        for t in threat_types:
            if t in RISK_FACTORS:
                scores[t] = (RISK_FACTORS[t].base_score, RISK_FACTORS[t].description)

        return scores

    def _calculate_behavioral_adjustment(self, profile: IpReputationProfile) -> float:
        adjustment = 0.0

        if profile.total_requests > 100:
            block_rate = profile.blocked_requests / profile.total_requests
            if block_rate > 0.5:
                adjustment += 15
            elif block_rate > 0.3:
                adjustment += 10
            elif block_rate > 0.1:
                adjustment += 5

        if profile.consecutive_high_risk > 5:
            adjustment += min(10, profile.consecutive_high_risk)

        if profile.asn_reputation > 0:
            adjustment -= profile.asn_reputation * 5

        if profile.country_reputation > 0:
            adjustment -= profile.country_reputation * 5

        return adjustment

    def _get_ip_profile(self, ip: str) -> Optional[IpReputationProfile]:
        cache_key = f"ip_guard:reputation:profile:{ip}"
        try:
            raw = self.cache.client.get(cache_key)
            if raw:
                data = json.loads(raw)
                return IpReputationProfile(**data)
        except Exception:
            pass
        return None

    def update_ip_profile(
        self,
        ip: str,
        risk_score: float,
        blocked: bool,
        country_code: Optional[str] = None,
    ) -> None:
        profile = self._get_ip_profile(ip)
        now = datetime.now().isoformat()

        if profile is None:
            profile = IpReputationProfile(ip=ip, first_seen=now)

        profile.last_seen = now
        profile.total_requests += 1
        if blocked:
            profile.blocked_requests += 1
            profile.consecutive_high_risk += 1
            profile.consecutive_normal = 0
        else:
            profile.allowed_requests += 1
            profile.consecutive_normal += 1
            profile.consecutive_high_risk = 0

        total = profile.total_requests
        profile.avg_risk_score = (profile.avg_risk_score * (total - 1) + risk_score) / total

        if country_code and country_code not in profile.countries:
            profile.countries.append(country_code)
            profile.country_reputation = self._country_reputation_db.get(country_code, 0.5)

        cache_key = f"ip_guard:reputation:profile:{ip}"
        try:
            self.cache.client.setex(cache_key, self._profile_cache_ttl, json.dumps(asdict(profile)))
        except Exception:
            pass

    def _load_country_reputation_db(self) -> Dict[str, float]:
        default_db = {
            "CN": 0.9, "US": 0.8, "JP": 0.85, "KR": 0.8, "DE": 0.85,
            "GB": 0.8, "FR": 0.8, "CA": 0.8, "AU": 0.8, "SG": 0.75,
            "RU": 0.3, "UA": 0.25, "BY": 0.2, "KP": 0.1, "IR": 0.2,
            "NG": 0.25, "BR": 0.5, "IN": 0.5, "PK": 0.35, "VN": 0.5,
            "TH": 0.5, "MY": 0.55, "ID": 0.45, "PH": 0.45, "BD": 0.35,
        }
        cache_key = "ip_guard:reputation:country_db"
        try:
            raw = self.cache.client.get(cache_key)
            if raw:
                return json.loads(raw)
        except Exception:
            pass
        return default_db

    def _load_asn_reputation_db(self) -> Dict[int, float]:
        default_db = {
            13335: 0.8, 14618: 0.8, 16509: 0.8, 8075: 0.8,
            37963: 0.7, 45090: 0.7, 38365: 0.7, 26496: 0.7,
            63949: 0.6, 20446: 0.6, 13414: 0.5,
        }
        cache_key = "ip_guard:reputation:asn_db"
        try:
            raw = self.cache.client.get(cache_key)
            if raw:
                return {int(k): v for k, v in json.loads(raw).items()}
        except Exception:
            pass
        return default_db

    def get_ip_reputation_report(self, ip: str) -> Dict[str, Any]:
        profile = self._get_ip_profile(ip)
        if not profile:
            return {"ip": ip, "found": False}

        threat_intel_info = {}
        try:
            raw = self.cache.client.get(f"ip_guard:threat_intel:query:{ip}")
            if raw:
                threat_intel_info = json.loads(raw)
        except Exception:
            pass

        return {
            "ip": ip,
            "found": True,
            "profile": {
                "total_requests": profile.total_requests,
                "blocked_requests": profile.blocked_requests,
                "allowed_requests": profile.allowed_requests,
                "block_rate": round(profile.blocked_requests / profile.total_requests * 100, 2) if profile.total_requests > 0 else 0,
                "avg_risk_score": round(profile.avg_risk_score, 2),
                "first_seen": profile.first_seen,
                "last_seen": profile.last_seen,
                "consecutive_high_risk": profile.consecutive_high_risk,
                "countries": profile.countries,
                "threat_types": profile.threat_types,
            },
            "threat_intel": threat_intel_info,
            "reputation_score": profile.final_reputation_score,
            "risk_level": self._score_to_risk_level(profile.final_reputation_score),
        }

    def _score_to_risk_level(self, score: float) -> str:
        if score >= 80:
            return "critical"
        elif score >= 60:
            return "high"
        elif score >= 40:
            return "medium"
        elif score >= 20:
            return "low"
        else:
            return "minimal"


def asdict(obj):
    if hasattr(obj, "__dataclass_fields__"):
        return {f: asdict(getattr(obj, f)) for f in obj.__dataclass_fields__}
    elif isinstance(obj, list):
        return [asdict(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: asdict(v) for k, v in obj.items()}
    else:
        return obj
