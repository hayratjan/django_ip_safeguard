"""定时从远程拉取中国内 / 国际 CIDR 列表并写入 Redis（建议由 crontab/systemd timer 每日执行）。"""

from django.core.management.base import BaseCommand

from django_ip_safeguard.conf import get_settings
from django_ip_safeguard.services.geo_ip_pool_sync import sync_all_geo_pools


class Command(BaseCommand):
    help = "同步地理 IP 池（中国内、国际）到 Redis，供中间件按策略匹配"

    def handle(self, *args, **options):
        cfg = get_settings()
        summary = sync_all_geo_pools(cfg)
        for item in summary.get("results") or []:
            if item.get("skipped"):
                self.stdout.write(self.style.WARNING(item.get("message") or str(item)))
            elif item.get("ok"):
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[{item['pool_key']}] 成功 行数={item.get('line_count')} "
                        f"v4区间={item.get('v4_interval_count')} v6={item.get('v6_net_count')}"
                    )
                )
            else:
                self.stdout.write(self.style.ERROR(f"[{item.get('pool_key')}] 失败: {item.get('error')}"))
