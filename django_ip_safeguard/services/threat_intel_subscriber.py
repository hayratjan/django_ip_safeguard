import ipaddress
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from django_ip_safeguard.conf import IpGuardSettings
from django_ip_safeguard.services.cache import RedisCacheService
from django_ip_safeguard.types import ThreatIntelEntry

logger = logging.getLogger(__name__)

DEFAULT_THREAT_FEEDS = {
    "spamhaus_drop": {
        "url": "https://www.spamhaus.org/drop/drop.txt",
        "format": "cidr_list",
        "threat_type": "botnet",
        "auto_ban": True,
        "ttl": 86400,
        "description": "Spamhaus DROP - 已知恶意IP段",
    },
    "spamhaus_edrop": {
        "url": "https://www.spamhaus.org/drop/edrop.txt",
        "format": "cidr_list",
        "threat_type": "botnet",
        "auto_ban": True,
        "ttl": 86400,
        "description": "Spamhaus EDROP - 扩展恶意IP段",
    },
    "tor_exit_nodes": {
        "url": "https://check.torproject.org/torbulkexitlist",
        "format": "ip_list",
        "threat_type": "tor",
        "auto_ban": False,
        "ttl": 3600,
        "description": "Tor出口节点列表",
    },
    "emerging_threats": {
        "url": "https://rules.emergingthreats.net/fwrules/emerging-Block-IPs.txt",
        "format": "ip_list",
        "threat_type": "malware",
        "auto_ban": True,
        "ttl": 86400,
        "description": "Emerging Threats 已知恶意IP",
    },
    "ci Army": {
        "url": "https://cinsarmy.com/my-lists/optimized/ci-badguys.txt",
        "format": "ip_list",
        "threat_type": "scanner",
        "auto_ban": True,
        "ttl": 86400,
        "description": "CINS Army - 恶意扫描源",
    },
    "dshield_top": {
        "url": "https://www.dshield.org/feeds/suspiciousdomains.txt",
        "format": "ip_list",
        "threat_type": "scanner",
        "auto_ban": True,
        "ttl": 86400,
        "description": "DShield 可疑IP列表",
    },
}

ABUSEIPDB_CATEGORIES = {
    "dns_compromise": 1,
    "dns_poisoning": 2,
    "fraud_orders": 3,
    "ddos_attack": 4,
    "ftp_brute": 5,
    "ping_of_death": 6,
    "phishing": 7,
    "fraud_cc": 8,
    "open_proxy": 9,
    "web_spam": 10,
    "email_spam": 11,
    "blog_spam": 12,
    "port_scan": 14,
    "hacking": 15,
    "sql_injection": 16,
    "backdoor": 17,
    "transgression": 18,
    "bot": 19,
    "web_attack": 20,
    "ssh_brute": 21,
}


@dataclass
class AbuseIPDBReport:
    ip_address: str
    categories: List[int]
    timestamp: str = ""
    reporter_count: int = 0


@dataclass
class ThreatFeedStats:
    feed_name: str
    entry_count: int
    last_updated: str
    auto_ban_count: int
    source: str
    threat_type: str


@dataclass
class ThreatIntelStats:
    total_feeds: int = 0
    total_entries: int = 0
    total_auto_bans: int = 0
    feeds: List[ThreatFeedStats] = field(default_factory=list)
    last_full_sync: str = ""


class EnhancedThreatIntelSubscriber:
    """增强版威胁情报订阅服务：支持更多数据源和统计分析"""

    def __init__(self, cache_service: RedisCacheService, config: IpGuardSettings):
        self.cache = cache_service
        self.config = config
        self._stats_key = "ip_guard:threat_intel:stats"

    def sync_feed(self, feed_name: str, feed_config: Dict[str, Any]) -> Dict[str, Any]:
        url = feed_config.get("url", "")
        if not url:
            return {"ok": False, "feed": feed_name, "error": "未配置URL"}

        try:
            text = self._fetch_feed(url, timeout=60.0)
        except Exception as exc:
            logger.exception("威胁情报拉取失败: %s - %s", feed_name, exc)
            return {"ok": False, "feed": feed_name, "error": str(exc)[:500]}

        feed_format = feed_config.get("format", "ip_list")
        threat_type = feed_config.get("threat_type", "unknown")
        auto_ban = feed_config.get("auto_ban", False)
        ttl = feed_config.get("ttl", 86400)

        entries = self._parse_feed(text, feed_format, threat_type, feed_name, auto_ban, ttl)

        if not entries:
            return {"ok": True, "feed": feed_name, "count": 0, "auto_ban_count": 0}

        self._store_entries(entries, feed_name, threat_type, ttl)

        auto_ban_count = 0
        if auto_ban:
            auto_ban_count = self._apply_auto_ban(entries, ttl)

        self._update_feed_stats(feed_name, len(entries), auto_ban_count, threat_type, feed_config.get("description", ""))

        logger.info(
            "威胁情报同步完成: %s, 条目=%s, 自动封禁=%s",
            feed_name, len(entries), auto_ban_count,
        )
        return {
            "ok": True,
            "feed": feed_name,
            "count": len(entries),
            "auto_ban_count": auto_ban_count,
        }

    def sync_all_feeds(self) -> Dict[str, Any]:
        feeds = self._get_active_feeds()
        results = []
        total_entries = 0
        total_auto_bans = 0
        for name, feed_config in feeds.items():
            result = self.sync_feed(name, feed_config)
            results.append(result)
            if result.get("ok"):
                total_entries += result.get("count", 0)
                total_auto_bans += result.get("auto_ban_count", 0)

        self._update_overall_stats(len(feeds), total_entries, total_auto_bans)

        return {"results": results, "total_entries": total_entries, "total_auto_bans": total_auto_bans}

    def get_stats(self) -> ThreatIntelStats:
        stats = ThreatIntelStats()
        try:
            stats_data = self.cache.client.get(self._stats_key)
            if stats_data:
                data = json.loads(stats_data)
                stats.total_feeds = data.get("total_feeds", 0)
                stats.total_entries = data.get("total_entries", 0)
                stats.total_auto_bans = data.get("total_auto_bans", 0)
                stats.last_full_sync = data.get("last_full_sync", "")
        except Exception:
            pass

        try:
            feeds_data = self.cache.client.get(f"{self._stats_key}:feeds")
            if feeds_data:
                feeds_list = json.loads(feeds_data)
                for f in feeds_list:
                    stats.feeds.append(ThreatFeedStats(
                        feed_name=f.get("feed_name", ""),
                        entry_count=f.get("entry_count", 0),
                        last_updated=f.get("last_updated", ""),
                        auto_ban_count=f.get("auto_ban_count", 0),
                        source=f.get("source", ""),
                        threat_type=f.get("threat_type", ""),
                    ))
        except Exception:
            pass

        return stats

    def query_ip_reputation(self, ip: str) -> Dict[str, Any]:
        result = {
            "ip": ip,
            "threat_types": [],
            "sources": [],
            "confidence": 0,
            "last_reported": None,
            "report_count": 0,
        }

        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return result

        feeds = self._get_active_feeds()
        for feed_name, feed_config in feeds.items():
            threat_type = feed_config.get("threat_type", "unknown")

            try:
                ip_key = f"ip_guard:threat_intel:{feed_name}:ips"
                if self.cache.client.sismember(ip_key, ip):
                    result["threat_types"].append(threat_type)
                    result["sources"].append(feed_name)
                    result["confidence"] = min(100, result["confidence"] + 30)
                    continue
            except Exception:
                pass

            try:
                cidr_key = f"ip_guard:threat_intel:{feed_name}:cidrs"
                cidrs = self.cache.client.smembers(cidr_key)
                for cidr_str in cidrs:
                    try:
                        if addr in ipaddress.ip_network(cidr_str, strict=False):
                            result["threat_types"].append(threat_type)
                            result["sources"].append(feed_name)
                            result["confidence"] = min(100, result["confidence"] + 20)
                            break
                    except ValueError:
                        continue
            except Exception:
                pass

        return result

    def check_abuseipdb(self, ip: str, api_key: str = "") -> Optional[Dict[str, Any]]:
        if not api_key:
            api_key = getattr(self.config, 'abuseipdb_api_key', "") or os.getenv("ABUSEIPDB_API_KEY", "")
        if not api_key:
            return None

        cache_key = f"ip_guard:abuseipdb:{ip}"
        try:
            cached = self.cache.client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

        url = "https://api.abuseipdb.com/api/v2/check"
        headers = {"Key": api_key, "Accept": "application/json"}
        params = {"ipAddress": ip, "maxAgeInDays": 90}

        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                resp = client.get(url, headers=headers, params=params)
                if resp.status_code == 429:
                    logger.warning("AbuseIPDB API 速率限制")
                    return None
                if resp.status_code != 200:
                    return None

                data = resp.json().get("data", {})
                result = {
                    "ip": ip,
                    "is_public": data.get("isPublic", False),
                    "ip_version": data.get("ipVersion", 0),
                    "is_whitelisted": data.get("isWhitelisted", False),
                    "abuse_confidence_score": data.get("abuseConfidenceScore", 0),
                    "country_code": data.get("countryCode", ""),
                    "usage_type": data.get("usageType", ""),
                    "isp": data.get("isp", ""),
                    "domain": data.get("domain", ""),
                    "total_reports": data.get("totalReports", 0),
                    "numDistinctUsers": data.get("numDistinctUsers", 0),
                    "last_reported_at": data.get("lastReportedAt", ""),
                }

                self.cache.client.setex(cache_key, 86400, json.dumps(result))
                return result
        except Exception as exc:
            logger.warning("AbuseIPDB 查询失败: %s", exc)
            return None

    def _get_active_feeds(self) -> Dict[str, Dict[str, Any]]:
        custom_feeds = {}
        if self.config.threat_intel_custom_feeds:
            try:
                custom_feeds = json.loads(self.config.threat_intel_custom_feeds)
            except (json.JSONDecodeError, TypeError):
                pass

        active = dict(DEFAULT_THREAT_FEEDS)
        if not self.config.threat_intel_spamhaus_enabled:
            active.pop("spamhaus_drop", None)
            active.pop("spamhaus_edrop", None)
        if not self.config.threat_intel_tor_enabled:
            active.pop("tor_exit_nodes", None)
        if not self.config.threat_intel_emerging_enabled:
            active.pop("emerging_threats", None)

        active.update(custom_feeds)
        return active

    def _fetch_feed(self, url: str, timeout: float = 60.0) -> str:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError(f"不支持的URL协议: {parsed.scheme}")
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.text

    def _parse_feed(
        self,
        text: str,
        feed_format: str,
        threat_type: str,
        source: str,
        auto_ban: bool,
        ttl: int,
    ) -> List[ThreatIntelEntry]:
        entries = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or line.startswith(";"):
                continue
            if feed_format == "cidr_list":
                entry = self._parse_cidr_line(line, threat_type, source, auto_ban, ttl)
                if entry:
                    entries.append(entry)
            elif feed_format == "ip_list":
                entry = self._parse_ip_line(line, threat_type, source, auto_ban, ttl)
                if entry:
                    entries.append(entry)
            elif feed_format == "json":
                entry = self._parse_json_line(line, threat_type, source, auto_ban, ttl)
                if entry:
                    entries.append(entry)
        return entries

    def _parse_cidr_line(self, line: str, threat_type: str, source: str, auto_ban: bool, ttl: int) -> Optional[ThreatIntelEntry]:
        parts = line.split(";")
        cidr = parts[0].strip()
        try:
            ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            return None
        description = parts[1].strip() if len(parts) > 1 else ""
        return ThreatIntelEntry(
            ip_or_cidr=cidr,
            threat_type=threat_type,
            source=source,
            description=description,
            auto_ban=auto_ban,
            ttl=ttl,
        )

    def _parse_ip_line(self, line: str, threat_type: str, source: str, auto_ban: bool, ttl: int) -> Optional[ThreatIntelEntry]:
        ip = line.strip()
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            return None
        return ThreatIntelEntry(
            ip_or_cidr=ip,
            threat_type=threat_type,
            source=source,
            auto_ban=auto_ban,
            ttl=ttl,
        )

    def _parse_json_line(self, line: str, threat_type: str, source: str, auto_ban: bool, ttl: int) -> Optional[ThreatIntelEntry]:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return None
        ip_or_cidr = data.get("ip") or data.get("cidr") or data.get("network", "")
        if not ip_or_cidr:
            return None
        return ThreatIntelEntry(
            ip_or_cidr=ip_or_cidr,
            threat_type=data.get("threat_type", threat_type),
            source=source,
            confidence=int(data.get("confidence", 0)),
            description=data.get("description", ""),
            auto_ban=data.get("auto_ban", auto_ban),
            ttl=int(data.get("ttl", ttl)),
        )

    def _store_entries(self, entries: List[ThreatIntelEntry], feed_name: str, threat_type: str, ttl: int) -> None:
        ip_list = []
        cidr_list = []
        for e in entries:
            if "/" in e.ip_or_cidr:
                cidr_list.append(e.ip_or_cidr)
            else:
                ip_list.append(e.ip_or_cidr)

        try:
            if ip_list:
                key = f"ip_guard:threat_intel:{feed_name}:ips"
                self.cache.client.delete(key)
                self.cache.client.sadd(key, *ip_list)
                self.cache.client.expire(key, ttl)

            if cidr_list:
                key = f"ip_guard:threat_intel:{feed_name}:cidrs"
                self.cache.client.delete(key)
                self.cache.client.sadd(key, *cidr_list)
                self.cache.client.expire(key, ttl)
        except Exception as exc:
            logger.warning("存储威胁情报失败: %s", exc)

        self._update_local_risk_caches(entries, threat_type)

    def _update_local_risk_caches(self, entries: List[ThreatIntelEntry], threat_type: str) -> None:
        if threat_type == "tor":
            ips = [e.ip_or_cidr for e in entries if "/" not in e.ip_or_cidr]
            if ips:
                try:
                    self.cache.client.set("ip_guard:threat_intel:tor_exit_nodes", json.dumps(ips))
                except Exception:
                    pass
        elif threat_type in ("botnet", "malware"):
            cidrs = [e.ip_or_cidr for e in entries if "/" in e.ip_or_cidr]
            if cidrs:
                try:
                    existing = self.cache.client.get("ip_guard:threat_intel:botnet_cidrs")
                    existing_list = json.loads(existing) if existing else []
                    merged = list(set(existing_list + cidrs))
                    self.cache.client.set("ip_guard:threat_intel:botnet_cidrs", json.dumps(merged))
                except Exception:
                    pass

    def _apply_auto_ban(self, entries: List[ThreatIntelEntry], ttl: int) -> int:
        count = 0
        for entry in entries:
            if not entry.auto_ban:
                continue
            if "/" in entry.ip_or_cidr:
                continue
            try:
                reason = f"威胁情报自动封禁({entry.source}): {entry.description or entry.threat_type}"
                self.cache.set_ban(ip=entry.ip_or_cidr, reason=reason, ttl=ttl)
                count += 1
            except Exception:
                continue
        return count

    def _update_feed_stats(self, feed_name: str, entry_count: int, auto_ban_count: int, threat_type: str, description: str) -> None:
        try:
            feeds_data = self.cache.client.get(f"{self._stats_key}:feeds")
            feeds_list = json.loads(feeds_data) if feeds_data else []

            for f in feeds_list:
                if f.get("feed_name") == feed_name:
                    f["entry_count"] = entry_count
                    f["auto_ban_count"] = auto_ban_count
                    f["last_updated"] = datetime.now().isoformat()
                    break
            else:
                feeds_list.append({
                    "feed_name": feed_name,
                    "entry_count": entry_count,
                    "auto_ban_count": auto_ban_count,
                    "last_updated": datetime.now().isoformat(),
                    "source": description,
                    "threat_type": threat_type,
                })

            self.cache.client.set(f"{self._stats_key}:feeds", json.dumps(feeds_list))
        except Exception:
            pass

    def _update_overall_stats(self, total_feeds: int, total_entries: int, total_auto_bans: int) -> None:
        try:
            stats = {
                "total_feeds": total_feeds,
                "total_entries": total_entries,
                "total_auto_bans": total_auto_bans,
                "last_full_sync": datetime.now().isoformat(),
            }
            self.cache.client.set(self._stats_key, json.dumps(stats))
        except Exception:
            pass


ThreatIntelSubscriber = EnhancedThreatIntelSubscriber
