import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone

from django_ip_safeguard.conf import get_settings
from django_ip_safeguard.models import IpAccessLog, IpReputationHistory

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "生成 IP 信誉快照：统计近期访问日志，计算风险趋势，写入 IpReputationHistory"

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours",
            type=int,
            default=0,
            help="统计最近 N 小时的数据（默认使用配置中的间隔）",
        )
        parser.add_argument(
            "--top-n",
            type=int,
            default=500,
            help="仅处理访问次数最高的前 N 个 IP（默认 500）",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="仅显示统计结果，不写入数据库",
        )

    def handle(self, *args, **options):
        cfg = get_settings()
        hours = options["hours"] or max(1, cfg.ip_reputation_snapshot_interval // 3600)
        top_n = options["top_n"]
        dry_run = options["dry_run"]

        if not cfg.ip_reputation_enabled:
            self.stdout.write(
                self.style.WARNING(
                    "IP 信誉快照功能未启用。请在 settings.py 中设置 IP_GUARD_IP_REPUTATION_ENABLED = True"
                )
            )
            return

        now = timezone.now()
        since_1h = now - timedelta(hours=1)
        since_24h = now - timedelta(hours=24)
        since_window = now - timedelta(hours=hours)

        self.stdout.write(
            self.style.HTTP_INFO(
                f"正在生成 IP 信誉快照 (统计窗口: {hours}小时, Top {top_n})..."
            )
        )

        top_ips = (
            IpAccessLog.objects.filter(created_at__gte=since_window)
            .values("ip")
            .annotate(access_count=Count("id"))
            .order_by("-access_count")[:top_n]
        )

        ip_list = list(top_ips)
        self.stdout.write(f"发现 {len(ip_list)} 个活跃 IP")

        created_count = 0
        skipped_count = 0

        for entry in ip_list:
            ip = entry["ip"]

            latest_log = (
                IpAccessLog.objects.filter(ip=ip)
                .order_by("-created_at")
                .first()
            )
            if not latest_log:
                continue

            block_1h = IpAccessLog.objects.filter(
                ip=ip, decision="block", created_at__gte=since_1h
            ).count()
            allow_1h = IpAccessLog.objects.filter(
                ip=ip, decision="allow", created_at__gte=since_1h
            ).count()
            block_24h = IpAccessLog.objects.filter(
                ip=ip, decision="block", created_at__gte=since_24h
            ).count()
            allow_24h = IpAccessLog.objects.filter(
                ip=ip, decision="allow", created_at__gte=since_24h
            ).count()

            trend = self._calculate_trend(ip, latest_log.risk_score, block_24h, allow_24h)

            if dry_run:
                self.stdout.write(
                    f"  {ip}: risk={latest_log.risk_score} trend={trend} "
                    f"1h(block={block_1h}/allow={allow_1h}) "
                    f"24h(block={block_24h}/allow={allow_24h})"
                )
                continue

            try:
                IpReputationHistory.objects.create(
                    ip=ip,
                    country_code=latest_log.country_code,
                    asn=latest_log.asn,
                    risk_score=latest_log.risk_score,
                    risk_tags=latest_log.risk_tags or [],
                    is_datacenter=latest_log.is_datacenter,
                    is_proxy=latest_log.is_proxy,
                    is_vpn=latest_log.is_vpn,
                    is_tor=latest_log.is_tor,
                    block_count_1h=block_1h,
                    allow_count_1h=allow_1h,
                    block_count_24h=block_24h,
                    allow_count_24h=allow_24h,
                    trend=trend,
                    source="auto_snapshot",
                )
                created_count += 1
            except Exception as exc:
                logger.warning("写入信誉快照失败: %s - %s", ip, exc)
                skipped_count += 1

        if dry_run:
            self.stdout.write(self.style.WARNING("(dry-run 模式，未写入数据库)"))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"信誉快照完成: 新增={created_count}, 跳过={skipped_count}"
                )
            )

    def _calculate_trend(self, ip: str, current_score: int, block_24h: int, allow_24h: int) -> str:
        last_snapshot = (
            IpReputationHistory.objects.filter(ip=ip)
            .order_by("-created_at")
            .first()
        )
        if not last_snapshot:
            if current_score >= 50 or block_24h > allow_24h:
                return "rising"
            return "stable"

        score_diff = current_score - last_snapshot.risk_score
        if score_diff > 10:
            return "rising"
        elif score_diff < -10:
            return "declining"
        return "stable"
