"""定时从远程拉取中国内 / 国际 CIDR 列表并写入 Redis（建议由 crontab/systemd timer 每日执行）。支持多数据源备份与自动切换。"""

from django.core.management.base import BaseCommand

from django_ip_safeguard.conf import get_settings
from django_ip_safeguard.services.geo_ip_pool_sync import sync_all_geo_pools


class Command(BaseCommand):
    help = "同步地理 IP 池（中国内、国际）到 Redis，支持多数据源备份自动切换"

    def add_arguments(self, parser):
        parser.add_argument(
            "--pool",
            type=str,
            default="",
            help="仅同步指定池（china / international），不指定则同步全部",
        )
        parser.add_argument(
            "--no-fallback",
            action="store_true",
            default=False,
            help="禁用多源备份，仅使用主数据源",
        )

    def handle(self, *args, **options):
        cfg = get_settings()
        pool = options["pool"]
        no_fallback = options["no_fallback"]

        if no_fallback:
            original = cfg.geo_pool_multi_source_enabled
            object.__setattr__(cfg, "geo_pool_multi_source_enabled", False)

        summary = sync_all_geo_pools(cfg)

        if no_fallback:
            object.__setattr__(cfg, "geo_pool_multi_source_enabled", original)

        for item in summary.get("results") or []:
            pool_key = item.get("pool_key", "")

            if pool and pool.lower() != pool_key.lower():
                continue

            if item.get("skipped"):
                self.stdout.write(self.style.WARNING(item.get("message") or str(item)))
            elif item.get("ok"):
                source_url = item.get("source_url", "")
                extra = f" 来源={source_url[:60]}" if source_url else ""
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[{pool_key}] 成功 行数={item.get('line_count')} "
                        f"v4区间={item.get('v4_interval_count')} v6={item.get('v6_net_count')}{extra}"
                    )
                )
            else:
                self.stdout.write(self.style.ERROR(f"[{pool_key}] 失败: {item.get('error')}"))
