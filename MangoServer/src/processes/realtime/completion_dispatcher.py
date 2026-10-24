import asyncio
from datetime import datetime
from typing import Any

from channels.db import database_sync_to_async
from django.db.models import Q
from django.utils import timezone

from src.apps.system.enums import ExecutorTaskStatusEnum
from src.apps.system.services.socket_link.message_service import SocketMessageService
from src.apps.task_center.selectors.querysets import TaskCenterQuerySelector
from src.apps.task_center.services.execution.executor_task import ExecutorTaskService
from src.common.logging import log
from src.processes.realtime.registry import LocalConnectionRegistry


class ExecutorTaskCompletionDispatcher:
    """由持有真实 WebSocket 的 realtime-service 投递任务完成通知。"""

    def __init__(
            self,
            registry: LocalConnectionRegistry,
            *,
            poll_interval: float = 1.0,
            batch_size: int = 100,
    ):
        self.registry = registry
        self.poll_interval = max(0.2, float(poll_interval))
        self.batch_size = min(max(1, int(batch_size)), 500)
        self._cursor_finished_at: datetime | None = None
        self._cursor_id = 0
        self._running = False

    async def initialize(self) -> None:
        cursor = await database_sync_to_async(self._latest_cursor)()
        if cursor is None:
            self._cursor_finished_at = timezone.now()
            self._cursor_id = 0
        else:
            self._cursor_finished_at, self._cursor_id = cursor

    async def run_forever(self) -> None:
        if self._cursor_finished_at is None:
            await self.initialize()
        self._running = True
        try:
            while self._running:
                tasks = await database_sync_to_async(self._load_batch)(
                    self._cursor_finished_at,
                    self._cursor_id,
                    self.batch_size,
                )
                if not tasks:
                    await asyncio.sleep(self.poll_interval)
                    continue
                for task in tasks:
                    await self._deliver(task)
                    self._cursor_finished_at = task.finished_at
                    self._cursor_id = task.id
        finally:
            self._running = False

    async def stop(self) -> None:
        self._running = False

    async def _deliver(self, task: Any) -> None:
        notice = SocketMessageService.build_executor_task_result_notice(task)
        if notice is None or task.created_by_id is None:
            return
        connections = await self.registry.get_web_connections(task.created_by_id)
        if not connections:
            return
        payload = notice.model_dump(mode="json")
        results = await asyncio.gather(
            *(connection.consumer.send_json(payload) for connection in connections),
            return_exceptions=True,
        )
        if results and all(isinstance(result, BaseException) for result in results):
            error = next(result for result in results if isinstance(result, BaseException))
            raise RuntimeError(
                f"任务完成通知发送失败：task_id={task.id}，connections={len(connections)}，error={error}"
            ) from error
        failed_count = sum(isinstance(result, BaseException) for result in results)
        if failed_count:
            log.system.warning(
                f"部分浏览器连接未收到任务完成通知：task_id={task.id}，"
                f"failed={failed_count}，total={len(connections)}"
            )

    @staticmethod
    def _base_queryset():
        return TaskCenterQuerySelector.executor_tasks().select_related("created_by").filter(
            task_type__in=ExecutorTaskService.COMPLETION_NOTIFICATION_TASK_TYPES,
            status__in=ExecutorTaskStatusEnum.terminal_values(),
            created_by__isnull=False,
            finished_at__isnull=False,
        )

    @classmethod
    def _latest_cursor(cls) -> tuple[datetime, int] | None:
        task = cls._base_queryset().order_by("-finished_at", "-id").first()
        if task is None:
            return None
        return task.finished_at, task.id

    @classmethod
    def _load_batch(
            cls,
            finished_at: datetime,
            task_id: int,
            limit: int,
    ) -> list[Any]:
        return list(
            cls._base_queryset()
            .filter(Q(finished_at__gt=finished_at) | Q(finished_at=finished_at, id__gt=task_id))
            .order_by("finished_at", "id")[:limit]
        )
