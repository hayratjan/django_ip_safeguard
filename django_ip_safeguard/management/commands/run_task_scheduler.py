import logging

from django.core.management.base import BaseCommand

from django_ip_safeguard.services.task_scheduler import scheduler

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "启动定时任务调度器（阻塞运行）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            default=False,
            help="仅执行一次所有到期的任务，不持续运行",
        )
        parser.add_argument(
            "--daemon",
            action="store_true",
            default=False,
            help="以后台守护进程模式运行",
        )

    def handle(self, *args, **options):
        if options["once"]:
            self.stdout.write("执行一次定时任务检查...")
            results = scheduler.run_once()
            self.stdout.write(f"已执行: {len(results['executed'])} 个任务")
            self.stdout.write(f"跳过: {len(results['skipped'])} 个任务")
            self.stdout.write(f"错误: {len(results['errors'])} 个任务")

            for r in results["executed"]:
                self.stdout.write(f"  ✓ {r['name']}: {r['status']}")
            for r in results["skipped"]:
                self.stdout.write(f"  - {r['name']}: {r['reason']}")
            for r in results["errors"]:
                self.stdout.write(self.style.ERROR(f"  ✗ {r['name']}: {r['error']}"))

            return

        self.stdout.write(self.style.HTTP_INFO("启动定时任务调度器..."))
        self.stdout.write("按 Ctrl+C 停止")

        try:
            scheduler.start()
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write("\n停止调度器...")
        finally:
            scheduler.stop()

        self.stdout.write(self.style.SUCCESS("调度器已停止"))
