import ipaddress
import json
import logging
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
}


class ThreatIntelSubscriber:
    """威胁情报订阅服务：从多个 Feed 拉取数据并写入 Redis。"""

    def __init__(self, cache_service: RedisCacheService, config: IpGuardSettings):
        self.cache = cache_service
        self.config = config

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
        for name, feed_config in feeds.items():
            result = self.sync_feed(name, feed_config)
            results.append(result)
        return {"results": results}

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

    def _parse_cidr_line(
        self, line: str, threat_type: str, source: str, auto_ban: bool, ttl: int
    ) -> Optional[ThreatIntelEntry]:
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

    def _parse_ip_line(
        self, line: str, threat_type: str, source: str, auto_ban: bool, ttl: int
    ) -> Optional[ThreatIntelEntry]:
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

    def _parse_json_line(
        self, line: str, threat_type: str, source: str, auto_ban: bool, ttl: int
    ) -> Optional[ThreatIntelEntry]:
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

    def _store_entries(
        self, entries: List[ThreatIntelEntry], feed_name: str, threat_type: str, ttl: int
    ) -> None:
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
                    self.cache.client.set(
                        "ip_guard:threat_intel:tor_exit_nodes",
                        json.dumps(ips),
                    )
                except Exception:
                    pass
        elif threat_type in ("botnet", "malware"):
            cidrs = [e.ip_or_cidr for e in entries if "/" in e.ip_or_cidr]
            if cidrs:
                try:
                    existing = self.cache.client.get("ip_guard:threat_intel:botnet_cidrs")
                    existing_list = json.loads(existing) if existing else []
                    merged = list(set(existing_list + cidrs))
                    self.cache.client.set(
                        "ip_guard:threat_intel:botnet_cidrs",
                        json.dumps(merged),
                    )
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

    def check_ip_in_feeds(self, ip: str) -> List[ThreatIntelEntry]:
        matches = []
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return matches

        feeds = self._get_active_feeds()
        for feed_name, feed_config in feeds.items():
            threat_type = feed_config.get("threat_type", "unknown")

            try:
                ip_key = f"ip_guard:threat_intel:{feed_name}:ips"
                if self.cache.client.sismember(ip_key, ip):
                    matches.append(ThreatIntelEntry(
                        ip_or_cidr=ip,
                        threat_type=threat_type,
                        source=feed_name,
                        auto_ban=feed_config.get("auto_ban", False),
                    ))
                    continue
            except Exception:
                pass

            try:
                cidr_key = f"ip_guard:threat_intel:{feed_name}:cidrs"
                cidrs = self.cache.client.smembers(cidr_key)
                for cidr_str in cidrs:
                    try:
                        if addr in ipaddress.ip_network(cidr_str, strict=False):
                            matches.append(ThreatIntelEntry(
                                ip_or_cidr=cidr_str,
                                threat_type=threat_type,
                                source=feed_name,
                                auto_ban=feed_config.get("auto_ban", False),
                            ))
                            break
                    except ValueError:
                        continue
            except Exception:
                pass

        return matches
