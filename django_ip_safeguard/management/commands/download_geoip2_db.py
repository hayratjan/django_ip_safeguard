import gzip
import logging
import os
import shutil

import httpx
from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)

GEOLITE2_CITY_URL = "https://git.io/GeoLite2-City.mmdb"
GEOLITE2_ASN_URL = "https://git.io/GeoLite2-ASN.mmdb"

MAXMIND_CITY_URL = (
    "https://download.maxmind.com/app/geoip_download?"
    "edition_id=GeoLite2-City&license_key={license_key}&suffix=tar.gz"
)
MAXMIND_ASN_URL = (
    "https://download.maxmind.com/app/geoip_download?"
    "edition_id=GeoLite2-ASN&license_key={license_key}&suffix=tar.gz"
)

MIRROR_URLS = {
    "city": [
        "https://raw.gitmirror.com/adysec/IP_database/main/geolite/GeoLite2-City.mmdb",
        "https://mirror.ghproxy.com/https://raw.githubusercontent.com/adysec/IP_database/main/geolite/GeoLite2-City.mmdb",
        "https://ghproxy.net/https://raw.githubusercontent.com/adysec/IP_database/main/geolite/GeoLite2-City.mmdb",
        "https://raw.githubusercontent.com/adysec/IP_database/main/geolite/GeoLite2-City.mmdb",
    ],
    "asn": [
        "https://raw.gitmirror.com/adysec/IP_database/main/geolite/GeoLite2-ASN.mmdb",
        "https://mirror.ghproxy.com/https://raw.githubusercontent.com/adysec/IP_database/main/geolite/GeoLite2-ASN.mmdb",
        "https://ghproxy.net/https://raw.githubusercontent.com/adysec/IP_database/main/geolite/GeoLite2-ASN.mmdb",
        "https://raw.githubusercontent.com/adysec/IP_database/main/geolite/GeoLite2-ASN.mmdb",
    ],
}


class Command(BaseCommand):
    help = "下载 MaxMind GeoLite2 数据库（City + ASN），用于本地离线 IP 地理位置和 ASN 查询"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            type=str,
            default="",
            help="数据库保存目录（默认: 项目根目录下的 geoip2_data/）",
        )
        parser.add_argument(
            "--license-key",
            type=str,
            default="",
            help="MaxMind License Key（从 MaxMind 官网获取，免费注册）",
        )
        parser.add_argument(
            "--city-only",
            action="store_true",
            default=False,
            help="仅下载 City 数据库",
        )
        parser.add_argument(
            "--asn-only",
            action="store_true",
            default=False,
            help="仅下载 ASN 数据库",
        )
        parser.add_argument(
            "--use-mirror",
            action="store_true",
            default=True,
            help="优先使用镜像源下载（默认启用）",
        )

    def handle(self, *args, **options):
        output_dir = options["output_dir"] or os.path.join(
            os.getcwd(), "geoip2_data"
        )
        license_key = options["license_key"] or os.getenv("MAXMIND_LICENSE_KEY", "")
        city_only = options["city_only"]
        asn_only = options["asn_only"]
        use_mirror = options["use_mirror"]

        os.makedirs(output_dir, exist_ok=True)

        results = {}

        if not asn_only:
            city_path = os.path.join(output_dir, "GeoLite2-City.mmdb")
            self.stdout.write(self.style.HTTP_INFO("正在下载 GeoLite2-City 数据库..."))
            ok = self._download_db(
                db_type="city",
                output_path=city_path,
                license_key=license_key,
                use_mirror=use_mirror,
            )
            results["city"] = {"path": city_path, "ok": ok}
            if ok:
                self.stdout.write(self.style.SUCCESS(f"GeoLite2-City 下载成功: {city_path}"))
            else:
                self.stdout.write(self.style.ERROR("GeoLite2-City 下载失败"))

        if not city_only:
            asn_path = os.path.join(output_dir, "GeoLite2-ASN.mmdb")
            self.stdout.write(self.style.HTTP_INFO("正在下载 GeoLite2-ASN 数据库..."))
            ok = self._download_db(
                db_type="asn",
                output_path=asn_path,
                license_key=license_key,
                use_mirror=use_mirror,
            )
            results["asn"] = {"path": asn_path, "ok": ok}
            if ok:
                self.stdout.write(self.style.SUCCESS(f"GeoLite2-ASN 下载成功: {asn_path}"))
            else:
                self.stdout.write(self.style.ERROR("GeoLite2-ASN 下载失败"))

        self.stdout.write(self.style.HTTP_INFO("\n配置提示:"))
        self.stdout.write("请在 Django settings.py 中添加以下配置:")
        if results.get("city", {}).get("ok"):
            self.stdout.write(f"  IP_GUARD_GEOIP2_CITY_DB_PATH = r'{results['city']['path']}'")
        if results.get("asn", {}).get("ok"):
            self.stdout.write(f"  IP_GUARD_GEOIP2_ASN_DB_PATH = r'{results['asn']['path']}'")
        self.stdout.write("  IP_GUARD_GEOIP2_ENABLED = True")

        if not all(r.get("ok") for r in results.values()):
            raise CommandError("部分数据库下载失败，请检查网络连接或使用 --license-key 参数")

    def _download_db(
        self,
        db_type: str,
        output_path: str,
        license_key: str,
        use_mirror: bool,
    ) -> bool:
        urls = self._build_urls(db_type, license_key, use_mirror)

        for url in urls:
            try:
                self.stdout.write(f"  尝试: {url[:80]}...")
                data = self._fetch(url)
                if data and len(data) > 1000:
                    self._save(data, output_path, url)
                    return True
            except Exception as exc:
                logger.warning("下载失败 %s: %s", url[:60], exc)
                self.stdout.write(f"  失败: {exc}")
                continue

        return False

    def _build_urls(self, db_type: str, license_key: str, use_mirror: bool) -> list:
        urls = []

        if use_mirror:
            mirror_urls = MIRROR_URLS.get(db_type, [])
            urls.extend(mirror_urls)

        if license_key:
            if db_type == "city":
                urls.append(MAXMIND_CITY_URL.format(license_key=license_key))
            elif db_type == "asn":
                urls.append(MAXMIND_ASN_URL.format(license_key=license_key))

        return urls

    def _fetch(self, url: str) -> bytes:
        with httpx.Client(timeout=300.0, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.content

    def _save(self, data: bytes, output_path: str, source_url: str) -> None:
        if source_url.endswith(".tar.gz"):
            self._extract_tar_gz(data, output_path)
        elif source_url.endswith(".gz"):
            self._extract_gz(data, output_path)
        else:
            with open(output_path, "wb") as f:
                f.write(data)

    def _extract_gz(self, data: bytes, output_path: str) -> None:
        tmp_gz = output_path + ".tmp.gz"
        with open(tmp_gz, "wb") as f:
            f.write(data)
        try:
            with gzip.open(tmp_gz, "rb") as f_in:
                with open(output_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
        finally:
            if os.path.exists(tmp_gz):
                os.remove(tmp_gz)

    def _extract_tar_gz(self, data: bytes, output_path: str) -> None:
        import tarfile

        tmp_tar = output_path + ".tmp.tar.gz"
        with open(tmp_tar, "wb") as f:
            f.write(data)
        try:
            with tarfile.open(tmp_tar, "r:gz") as tar:
                for member in tar.getmembers():
                    if member.name.endswith(".mmdb"):
                        f = tar.extractfile(member)
                        if f:
                            with open(output_path, "wb") as out:
                                shutil.copyfileobj(f, out)
                            return
        finally:
            if os.path.exists(tmp_tar):
                os.remove(tmp_tar)
