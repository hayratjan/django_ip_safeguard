import ipaddress
import json
import logging
import time
from typing import Dict, List, Optional, Set

from django_ip_safeguard.conf import IpGuardSettings
from django_ip_safeguard.services.cache import RedisCacheService
from django_ip_safeguard.types import IpIntel

logger = logging.getLogger(__name__)

_TOR_EXIT_CACHE: Dict[str, Tuple[float, Set[str]]] = {}
_BOTNET_CIDR_CACHE: Dict[str, Tuple[float, List[ipaddress.IPv4Network]]] = {}
_DATACENTER_ASN_CACHE: Dict[str, Tuple[float, Set[int]]] = {}


class LocalRiskRuleEngine:
    """
    本地风险规则引擎：不依赖外部 API 即可判定的规则。
    - Tor 出口节点检测
    - 僵尸网络 CIDR 检测
    - IDC/数据中心 ASN 检测
    - 代理/VPN 本地列表检测
    """

    def __init__(self, cache_service: RedisCacheService, config: IpGuardSettings):
        self.cache = cache_service
        self.config = config

    def evaluate(self, ip: str, ip_intel: IpIntel) -> List[str]:
        reasons = []

        tor_reason = self._check_tor_exit(ip)
        if tor_reason:
            reasons.append(tor_reason)
            ip_intel.is_tor = True
            if "tor" not in ip_intel.risk_tags:
                ip_intel.risk_tags.append("tor")

        botnet_reason = self._check_botnet_cidr(ip)
        if botnet_reason:
            reasons.append(botnet_reason)
            ip_intel.is_botnet = True
            if "botnet" not in ip_intel.risk_tags:
                ip_intel.risk_tags.append("botnet")

        dc_reason = self._check_datacenter(ip_intel)
        if dc_reason:
            reasons.append(dc_reason)
            ip_intel.is_datacenter = True
            if "datacenter" not in ip_intel.risk_tags:
                ip_intel.risk_tags.append("datacenter")

        proxy_reason = self._check_proxy_vpn(ip, ip_intel)
        if proxy_reason:
            reasons.append(proxy_reason)

        subnet_reason = self._check_subnet_attack(ip)
        if subnet_reason:
            reasons.append(subnet_reason)
            if "subnet_attack" not in ip_intel.risk_tags:
                ip_intel.risk_tags.append("subnet_attack")

        if reasons:
            extra_score = len(reasons) * 20
            ip_intel.risk_score = min(100, ip_intel.risk_score + extra_score)

        return reasons

    def _check_tor_exit(self, ip: str) -> Optional[str]:
        tor_nodes = self._load_tor_exit_nodes()
        if tor_nodes and ip in tor_nodes:
            return "Tor出口节点"
        return None

    def _check_botnet_cidr(self, ip: str) -> Optional[str]:
        botnet_nets = self._load_botnet_cidrs()
        if not botnet_nets:
            return None
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return None
        for net in botnet_nets:
            if addr in net:
                return f"命中僵尸网络CIDR: {net}"
        return None

    def _check_datacenter(self, ip_intel: IpIntel) -> Optional[str]:
        dc_asns = self._load_datacenter_asns()
        if not dc_asns or ip_intel.asn is None:
            return None
        if ip_intel.asn in dc_asns:
            return f"数据中心ASN: {ip_intel.asn}({ip_intel.asn_org or ''})"
        return None

    def _check_proxy_vpn(self, ip: str, ip_intel: IpIntel) -> Optional[str]:
        proxy_list = self._load_proxy_vpn_list()
        if not proxy_list:
            return None
        if ip in proxy_list:
            ip_intel.is_proxy = True
            if "proxy" not in ip_intel.risk_tags:
                ip_intel.risk_tags.append("proxy")
            return "代理/VPN节点"
        return None

    def _check_subnet_attack(self, ip: str) -> Optional[str]:
        try:
            addr = ipaddress.ip_address(ip)
            if addr.version != 4:
                return None
            octets = str(ip).split(".")
            if len(octets) != 4:
                return None
            subnet_prefix = ".".join(octets[:3])
        except ValueError:
            return None

        window_seconds = 300
        threshold = self.config.local_risk_subnet_attack_threshold
        if threshold <= 0:
            return None

        try:
            key = f"ip_guard:subnet:{subnet_prefix}"
            now = time.time()
            pipe = self.cache.client.pipeline()
            pipe.zremrangebyscore(key, 0, now - window_seconds)
            pipe.zadd(key, {ip: now})
            pipe.zcard(key)
            pipe.expire(key, window_seconds)
            _, _, count, _ = pipe.execute()
            if int(count) >= threshold:
                return f"同C段攻击关联({subnet_prefix}.0/24, {count}个IP)"
        except Exception:
            pass
        return None

    def _load_tor_exit_nodes(self) -> Set[str]:
        cache_key = "tor_exit_nodes"
        now = time.time()
        if cache_key in _TOR_EXIT_CACHE:
            exp, data = _TOR_EXIT_CACHE[cache_key]
            if now < exp:
                return data

        try:
            raw = self.cache.client.get("ip_guard:threat_intel:tor_exit_nodes")
            if raw:
                nodes = set(json.loads(raw))
                _TOR_EXIT_CACHE[cache_key] = (now + 3600, nodes)
                return nodes
        except Exception:
            pass

        _TOR_EXIT_CACHE[cache_key] = (now + 300, set())
        return set()

    def _load_botnet_cidrs(self) -> List[ipaddress.IPv4Network]:
        cache_key = "botnet_cidrs"
        now = time.time()
        if cache_key in _BOTNET_CIDR_CACHE:
            exp, data = _BOTNET_CIDR_CACHE[cache_key]
            if now < exp:
                return data

        try:
            raw = self.cache.client.get("ip_guard:threat_intel:botnet_cidrs")
            if raw:
                cidr_strs = json.loads(raw)
                nets = []
                for s in cidr_strs:
                    try:
                        nets.append(ipaddress.ip_network(s, strict=False))
                    except ValueError:
                        continue
                _BOTNET_CIDR_CACHE[cache_key] = (now + 3600, nets)
                return nets
        except Exception:
            pass

        _BOTNET_CIDR_CACHE[cache_key] = (now + 300, [])
        return []

    def _load_datacenter_asns(self) -> Set[int]:
        cache_key = "datacenter_asns"
        now = time.time()
        if cache_key in _DATACENTER_ASN_CACHE:
            exp, data = _DATACENTER_ASN_CACHE[cache_key]
            if now < exp:
                return data

        try:
            raw = self.cache.client.get("ip_guard:threat_intel:datacenter_asns")
            if raw:
                asns = set(json.loads(raw))
                _DATACENTER_ASN_CACHE[cache_key] = (now + 3600, asns)
                return asns
        except Exception:
            pass

        default_asns = {
            13335, 14618, 16509, 8075, 13414, 26496,
            20446, 63949, 45090, 37963, 45090, 38365,
        }
        _DATACENTER_ASN_CACHE[cache_key] = (now + 3600, default_asns)
        return default_asns

    def _load_proxy_vpn_list(self) -> Set[str]:
        try:
            raw = self.cache.client.get("ip_guard:threat_intel:proxy_vpn_list")
            if raw:
                return set(json.loads(raw))
        except Exception:
            pass
        return set()


def clear_local_risk_caches() -> None:
    _TOR_EXIT_CACHE.clear()
    _BOTNET_CIDR_CACHE.clear()
    _DATACENTER_ASN_CACHE.clear()
