import logging
import os
from datetime import datetime

from django.core.management.base import BaseCommand

from django_ip_safeguard.conf import get_settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "自动更新 GeoLite2 数据库（支持定时任务 cron 调用）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--check-only",
            action="store_true",
            default=False,
            help="仅检查更新，不下载",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="强制重新下载（即使数据库已存在）",
        )

    def handle(self, *args, **options):
        from django_ip_safeguard.management.commands.download_geoip2_db import Command as DownloadCommand

        cfg = get_settings()
        check_only = options["check_only"]
        force = options["force"]

        geoip2_dir = os.path.join(os.getcwd(), "geoip2_data")
        city_db = os.path.join(geoip2_dir, "GeoLite2-City.mmdb")
        asn_db = os.path.join(geoip2_dir, "GeoLite2-ASN.mmdb")

        city_exists = os.path.exists(city_db)
        asn_exists = os.path.exists(asn_db)

        if check_only:
            self.stdout.write(f"GeoLite2-City: {'已存在' if city_exists else '不存在'}")
            self.stdout.write(f"GeoLite2-ASN: {'已存在' if asn_exists else '不存在'}")
            if city_exists:
                mtime = datetime.fromtimestamp(os.path.getmtime(city_db))
                self.stdout.write(f"City 数据库更新时间: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
            if asn_exists:
                mtime = datetime.fromtimestamp(os.path.getmtime(asn_db))
                self.stdout.write(f"ASN 数据库更新时间: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
            return

        needs_update = force or not (city_exists and asn_exists)

        if not needs_update:
            city_age_days = (datetime.now().timestamp() - os.path.getmtime(city_db)) / 86400
            asn_age_days = (datetime.now().timestamp() - os.path.getmtime(asn_db)) / 86400

            if city_age_days > 7 or asn_age_days > 7:
                needs_update = True
                self.stdout.write(
                    self.style.WARNING(
                        f"数据库超过7天未更新 (City: {city_age_days:.1f}天, ASN: {asn_age_days:.1f}天)，将自动更新"
                    )
                )

        if not needs_update:
            self.stdout.write(self.style.SUCCESS("GeoLite2 数据库已是最新，无需更新"))
            return

        download_cmd = DownloadCommand()
        download_cmd.handle(
            output_dir=geoip2_dir,
            license_key=cfg.provider_api_key or os.getenv("MAXMIND_LICENSE_KEY", ""),
            use_mirror=True,
        )

        logger.info("GeoIP2 自动更新任务完成")
        self.stdout.write(self.style.SUCCESS("GeoLite2 数据库自动更新完成"))
