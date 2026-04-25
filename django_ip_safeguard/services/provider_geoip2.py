import logging
import os
from typing import Optional

from django_ip_safeguard.services.provider_base import BaseIpIntelProvider
from django_ip_safeguard.types import IpIntel

logger = logging.getLogger(__name__)


class GeoIP2LocalProvider(BaseIpIntelProvider):
    """
    基于 MaxMind GeoLite2 的本地离线查询 Provider。
    支持国家码、城市、经纬度、ASN 查询，零网络延迟。
    需要安装 geoip2 包并下载 GeoLite2-City.mmdb / GeoLite2-ASN.mmdb。
    """

    def __init__(self, city_db_path: str = "", asn_db_path: str = ""):
        self._city_reader = None
        self._asn_reader = None
        self._city_db_path = city_db_path
        self._asn_db_path = asn_db_path
        self._init_readers()

    def _init_readers(self) -> None:
        try:
            import geoip2.database
        except ImportError:
            logger.warning("geoip2 包未安装，本地 GeoIP 查询不可用。请执行: pip install geoip2")
            return

        if self._city_db_path and os.path.isfile(self._city_db_path):
            try:
                self._city_reader = geoip2.database.Reader(self._city_db_path)
                logger.info("GeoLite2-City 数据库已加载: %s", self._city_db_path)
            except Exception as exc:
                logger.warning("加载 GeoLite2-City 失败: %s", exc)
        else:
            if self._city_db_path:
                logger.warning("GeoLite2-City 数据库文件不存在: %s", self._city_db_path)

        if self._asn_db_path and os.path.isfile(self._asn_db_path):
            try:
                self._asn_reader = geoip2.database.Reader(self._asn_db_path)
                logger.info("GeoLite2-ASN 数据库已加载: %s", self._asn_db_path)
            except Exception as exc:
                logger.warning("加载 GeoLite2-ASN 失败: %s", exc)
        else:
            if self._asn_db_path:
                logger.warning("GeoLite2-ASN 数据库文件不存在: %s", self._asn_db_path)

    def is_available(self) -> bool:
        return self._city_reader is not None or self._asn_reader is not None

    def fetch_ip_intel(self, ip: str) -> IpIntel:
        intel = IpIntel(ip=ip, source="geoip2_local")

        if self._city_reader:
            try:
                resp = self._city_reader.city(ip)
                intel.country_code = resp.country.iso_code
                intel.country_name = resp.country.name
                intel.region = resp.subdivisions.most_specific.name if resp.subdivisions else None
                intel.city = resp.city.name
                intel.latitude = resp.location.latitude
                intel.longitude = resp.location.longitude
            except Exception:
                pass

        if self._asn_reader:
            try:
                resp = self._asn_reader.asn(ip)
                intel.asn = resp.autonomous_system_number
                intel.asn_org = resp.autonomous_system_organization
            except Exception:
                pass

        return intel

    def close(self) -> None:
        if self._city_reader:
            try:
                self._city_reader.close()
            except Exception:
                pass
        if self._asn_reader:
            try:
                self._asn_reader.close()
            except Exception:
                pass


_local_provider: Optional[GeoIP2LocalProvider] = None


def get_local_geoip_provider(city_db_path: str = "", asn_db_path: str = "") -> GeoIP2LocalProvider:
    global _local_provider
    if _local_provider is None:
        _local_provider = GeoIP2LocalProvider(city_db_path=city_db_path, asn_db_path=asn_db_path)
    return _local_provider


def reset_local_geoip_provider() -> None:
    global _local_provider
    if _local_provider is not None:
        _local_provider.close()
        _local_provider = None
