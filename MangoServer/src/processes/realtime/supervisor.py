import asyncio
from contextlib import suppress

from channels.db import database_sync_to_async

from src.apps.system.enums import RuntimeServiceName
from src.apps.system.services.runtime_center.heartbeat import ServiceHeartbeatService
from src.apps.system.services.runtime_center.system_error_event import SystemErrorEventSource
from src.apps.system.services.socket_link.connection_service import SocketConnectionService
from src.common.decorators.system_error import areport_system_error
from src.common.logging import log
from src.processes.realtime.completion_dispatcher import ExecutorTaskCompletionDispatcher
from src.processes.realtime.live_stream.registry import LiveStreamRegistry
from src.processes.realtime.live_stream.supervisor import LiveStreamSupervisor
from src.processes.realtime.registry import LocalConnectionRegistry


class RealtimeSupervisor:
    def __init__(
            self,
            registry: LocalConnectionRegistry,
            service_instance: str,
            live_stream_registry: LiveStreamRegistry,
            *,
            heartbeat_interval: float = 15.0,
            connection_flush_interval: float = 20.0,
    ):
        self.registry = registry
        self.service_instance = service_instance
        self.heartbeat_interval = heartbeat_interval
        self.connection_flush_interval = connection_flush_interval
        self.live_stream = LiveStreamSupervisor(live_stream_registry)
        self.completion_dispatcher = ExecutorTaskCompletionDispatcher(registry)
        self._tasks: dict[str, asyncio.Task] = {}
        self._running = False
        self._failure: BaseException | None = None
        self._failure_counts: dict[str, int] = {}

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        await database_sync_to_async(SocketConnectionService.disconnect_service)(self.service_instance)
        await self.completion_dispatcher.initialize()
        self._start_task("service_heartbeat", self._heartbeat_loop)
        self._start_task("connection_flush", self._connection_flush_loop)
        self._start_task("completion_notification", self.completion_dispatcher.run_forever)
        self._start_task("live_stream_cleanup", self.live_stream.run_forever)
        log.system.info(f"realtime-service 已启动：instance={self.service_instance}")

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        await self.completion_dispatcher.stop()
        await self.live_stream.stop()
        await self._flush_connections()
        await self.registry.close_all()
        tasks = list(self._tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()
        await database_sync_to_async(SocketConnectionService.disconnect_service)(self.service_instance)
        log.system.info(f"realtime-service 已停止：instance={self.service_instance}")

    def assert_healthy(self) -> None:
        if not self._running:
            raise RuntimeError("realtime-service 尚未启动或正在停止")

    def _start_task(self, name: str, coroutine_factory) -> None:
        task = asyncio.create_task(
            self._supervise(name, coroutine_factory),
            name=f"realtime:{name}",
        )
        task.add_done_callback(lambda completed, task_name=name: self._task_done(task_name, completed))
        self._tasks[name] = task

    def _task_done(self, name: str, task: asyncio.Task) -> None:
        if not self._running or task.cancelled():
            return
        with suppress(asyncio.CancelledError):
            error = task.exception()
            if error is not None:
                self._failure = error
                self._running = False
                log.system.error(f"realtime-service 长期协程异常退出：task={name}, error={error}")

    async def _supervise(self, name: str, coroutine_factory) -> None:
        while self._running:
            try:
                await coroutine_factory()
                if self._running:
                    raise RuntimeError("长期协程意外结束")
            except asyncio.CancelledError:
                raise
            except Exception as error:
                failure_count = self._failure_counts.get(name, 0) + 1
                self._failure_counts[name] = failure_count
                delay = min(30, 2 ** min(failure_count - 1, 4))
                await areport_system_error(
                    error,
                    source=SystemErrorEventSource.REALTIME,
                    request_path=f'realtime:{name}',
                    service_name=RuntimeServiceName.REALTIME,
                )
                log.system.error(
                    f"realtime-service 协程失败，{delay}s 后重启："
                    f"task={name}, failures={failure_count}, error={error}"
                )
                await asyncio.sleep(delay)

    async def _heartbeat_loop(self) -> None:
        while self._running:
            counts = await self.registry.counts()
            live_stream_counts = await self.live_stream.registry.stats()
            await ServiceHeartbeatService.abeat(
                RuntimeServiceName.REALTIME,
                instance_name=self.service_instance,
                metadata={
                    **counts,
                    "live_stream": live_stream_counts,
                    "event_loop_lag_ms": round(self.live_stream.event_loop_lag_ms, 2),
                },
            )
            await asyncio.sleep(self.heartbeat_interval)

    async def _connection_flush_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self.connection_flush_interval)
            await self._flush_connections()

    async def _flush_connections(self) -> None:
        dirty = await self.registry.drain_dirty_last_seen()
        if dirty:
            await database_sync_to_async(SocketConnectionService.bulk_touch)(dirty)
