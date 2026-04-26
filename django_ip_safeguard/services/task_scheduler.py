import logging
import threading
import time
from datetime import timedelta
from typing import Dict, List, Optional

from django.utils import timezone

logger = logging.getLogger(__name__)


class TaskScheduler:
    """
    定时任务调度器：
    - 支持间隔执行和 Cron 表达式
    - 后台线程运行，不阻塞主进程
    - 可通过 Django Management Command 调用
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._running = False
            self._thread: Optional[threading.Thread] = None
            self._check_interval = 60
            self._initialized = True

    def start(self) -> None:
        if self._running:
            logger.warning("TaskScheduler 已运行，跳过启动")
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("TaskScheduler 已启动")

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("TaskScheduler 已停止")

    def _run_loop(self) -> None:
        while self._running:
            try:
                self._check_and_run_tasks()
            except Exception as exc:
                logger.exception("任务调度循环异常: %s", exc)

            for _ in range(self._check_interval):
                if not self._running:
                    break
                time.sleep(1)

    def _check_and_run_tasks(self) -> None:
        from django_ip_safeguard.models import ScheduledTask

        now = timezone.now()
        tasks = ScheduledTask.objects.filter(enabled=True)

        for task in tasks:
            if self._should_run_task(task, now):
                logger.info("触发定时任务: %s", task.name)
                self._execute_task_async(task)

    def _should_run_task(self, task, now: timezone.datetime) -> bool:
        if task.next_run_at is None:
            task.next_run_at = task.calculate_next_run()
            task.save(update_fields=["next_run_at"])
            return False

        if now >= task.next_run_at:
            if task.last_run_at and task.last_run_status == "running":
                elapsed = (now - task.last_run_at).total_seconds()
                if elapsed < 300:
                    return False
            return True

        return False

    def _execute_task_async(self, task) -> None:
        thread = threading.Thread(target=self._execute_task, args=(task,), daemon=True)
        thread.start()

    def _execute_task(self, task) -> None:
        from django_ip_safeguard.models import TaskExecutionLog
        import time as time_module

        task.last_run_status = "running"
        task.save(update_fields=["last_run_status"])

        started_at = timezone.now()
        log = TaskExecutionLog.objects.create(
            task=task,
            status="running",
            started_at=started_at,
        )

        try:
            result = task.execute()
            completed_at = timezone.now()
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

            log.status = result.get("status", "unknown")
            log.completed_at = completed_at
            log.duration_ms = duration_ms
            log.output = result.get("output", "")[:5000]
            log.error = result.get("error", "")[:5000]
            log.save()

        except Exception as exc:
            log.status = "error"
            log.error = str(exc)[:5000]
            log.save()
            logger.exception("任务执行异常: %s", task.name)

    def run_once(self) -> Dict[str, List[Dict]]:
        results = {
            "executed": [],
            "skipped": [],
            "errors": [],
        }

        from django_ip_safeguard.models import ScheduledTask

        now = timezone.now()
        tasks = ScheduledTask.objects.filter(enabled=True)

        for task in tasks:
            if task.last_run_status == "running":
                if task.last_run_at and (now - task.last_run_at).total_seconds() < 300:
                    results["skipped"].append({
                        "name": task.name,
                        "reason": "上次执行仍在运行",
                    })
                    continue

            should_run = self._should_run_task(task, now)
            if should_run:
                try:
                    result = task.execute()
                    results["executed"].append({
                        "name": task.name,
                        "status": result.get("status"),
                        "output": result.get("output", "")[:200],
                    })
                except Exception as exc:
                    results["errors"].append({
                        "name": task.name,
                        "error": str(exc),
                    })
            else:
                results["skipped"].append({
                    "name": task.name,
                    "reason": f"未到执行时间，下次执行: {task.next_run_at}",
                })

        return results


scheduler = TaskScheduler()
