import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from django_ip_safeguard.conf import get_settings
from django_ip_safeguard.models import ThreatIntelFeedStatus
from django_ip_safeguard.services.cache import RedisCacheService
from django_ip_safeguard.services.threat_intel_subscriber import ThreatIntelSubscriber

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "同步威胁情报源（Spamhaus、Tor出口、Emerging Threats等），更新 Redis 缓存和数据库状态"

    def add_arguments(self, parser):
        parser.add_argument(
            "--feed",
            type=str,
            default="",
            help="仅同步指定情报源（如: spamhaus_drop, tor_exit_nodes），不指定则同步全部",
        )
        parser.add_argument(
            "--list-feeds",
            action="store_true",
            default=False,
            help="列出所有可用的情报源",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="强制同步，忽略启用状态",
        )

    def handle(self, *args, **options):
        cfg = get_settings()

        if not cfg.threat_intel_enabled and not options["force"]:
            self.stdout.write(
                self.style.WARNING(
                    "威胁情报订阅未启用。请在 settings.py 中设置 IP_GUARD_THREAT_INTEL_ENABLED = True "
                    "或使用 --force 强制同步。"
                )
            )
            return

        cache_service = RedisCacheService(cfg.redis_url)
        subscriber = ThreatIntelSubscriber(cache_service, cfg)

        if options["list_feeds"]:
            self._list_feeds(subscriber)
            return

        feed_name = options["feed"]
        if feed_name:
            self._sync_single_feed(subscriber, feed_name, options["force"])
        else:
            self._sync_all_feeds(subscriber)

    def _list_feeds(self, subscriber: ThreatIntelSubscriber) -> None:
        feeds = subscriber._get_active_feeds()
        self.stdout.write(self.style.HTTP_INFO("可用的威胁情报源:"))
        self.stdout.write("")
        for name, config in feeds.items():
            self.stdout.write(f"  {name}")
            self.stdout.write(f"    URL: {config.get('url', 'N/A')}")
            self.stdout.write(f"    格式: {config.get('format', 'N/A')}")
            self.stdout.write(f"    威胁类型: {config.get('threat_type', 'N/A')}")
            self.stdout.write(f"    自动封禁: {'是' if config.get('auto_ban') else '否'}")
            self.stdout.write(f"    描述: {config.get('description', 'N/A')}")
            self.stdout.write("")

    def _sync_single_feed(self, subscriber: ThreatIntelSubscriber, feed_name: str, force: bool) -> None:
        feeds = subscriber._get_active_feeds()
        if not force:
            all_feeds = subscriber._get_active_feeds()
            if feed_name not in all_feeds:
                from django_ip_safeguard.services.threat_intel_subscriber import DEFAULT_THREAT_FEEDS
                if feed_name not in DEFAULT_THREAT_FEEDS:
                    self.stdout.write(self.style.ERROR(f"未知的情报源: {feed_name}"))
                    self.stdout.write("使用 --list-feeds 查看所有可用源")
                    return

        feed_config = feeds.get(feed_name)
        if not feed_config:
            from django_ip_safeguard.services.threat_intel_subscriber import DEFAULT_THREAT_FEEDS
            feed_config = DEFAULT_THREAT_FEEDS.get(feed_name, {})

        self.stdout.write(self.style.HTTP_INFO(f"正在同步情报源: {feed_name}"))
        result = subscriber.sync_feed(feed_name, feed_config)
        self._print_result(result)
        self._update_db_status(feed_name, feed_config, result)

    def _sync_all_feeds(self, subscriber: ThreatIntelSubscriber) -> None:
        self.stdout.write(self.style.HTTP_INFO("正在同步所有威胁情报源..."))
        summary = subscriber.sync_all_feeds()

        for result in summary.get("results") or []:
            self._print_result(result)
            feed_name = result.get("feed", "")
            if feed_name:
                feeds = subscriber._get_active_feeds()
                feed_config = feeds.get(feed_name, {})
                self._update_db_status(feed_name, feed_config, result)

        total = sum(1 for r in (summary.get("results") or []) if r.get("ok"))
        failed = sum(1 for r in (summary.get("results") or []) if not r.get("ok"))
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"同步完成: 成功={total}, 失败={failed}")
        )

    def _print_result(self, result: dict) -> None:
        feed = result.get("feed", "unknown")
        if result.get("ok"):
            count = result.get("count", 0)
            auto_ban = result.get("auto_ban_count", 0)
            msg = f"  [{feed}] 成功: 条目={count}"
            if auto_ban > 0:
                msg += f", 自动封禁={auto_ban}"
            self.stdout.write(self.style.SUCCESS(msg))
        else:
            error = result.get("error", "未知错误")
            self.stdout.write(self.style.ERROR(f"  [{feed}] 失败: {error[:200]}"))

    def _update_db_status(self, feed_name: str, feed_config: dict, result: dict) -> None:
        try:
            defaults = {
                "feed_url": feed_config.get("url", "")[:512],
                "feed_format": feed_config.get("format", "ip_list"),
                "threat_type": feed_config.get("threat_type", "unknown"),
                "auto_ban": feed_config.get("auto_ban", False),
                "enabled": True,
            }
            if result.get("ok"):
                defaults["entry_count"] = result.get("count", 0)
                defaults["auto_ban_count"] = result.get("auto_ban_count", 0)
                defaults["last_ok_at"] = timezone.now()
                defaults["last_error"] = ""
            else:
                defaults["last_error"] = result.get("error", "")[:2000]

            ThreatIntelFeedStatus.objects.update_or_create(
                feed_name=feed_name,
                defaults=defaults,
            )
        except Exception as exc:
            logger.warning("更新威胁情报状态失败: %s - %s", feed_name, exc)
