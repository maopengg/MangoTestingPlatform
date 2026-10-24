import asyncio
import traceback

from src.services.ui.live_stream.client import UiLiveStreamClient
from src.services.ui.live_stream.environment import ensure_live_stream_supported
from src.services.ui.live_stream.runtime_registry import UiRuntimeRegistry
from src.tools.log_collector import log


class UiLiveStreamManager:
    _tasks: dict[str, asyncio.Task] = {}
    _clients: dict[str, UiLiveStreamClient] = {}
    _commands: dict[str, dict] = {}
    _starting: set[str] = set()
    _cancelled: set[str] = set()
    _lock = asyncio.Lock()

    @classmethod
    async def start(cls, command: dict) -> None:
        ensure_live_stream_supported()
        stream_id = command["stream_id"]
        log.debug(
            f"UI实时画面启动命令：stream={stream_id}，"
            f"type={command.get('execution_type')}，execution={command.get('execution_id')}"
        )
        async with cls._lock:
            existing = cls._tasks.get(stream_id)
            if (existing and not existing.done()) or stream_id in cls._starting:
                log.debug(f"UI实时画面启动忽略，任务已存在：stream={stream_id}")
                return
            cls._starting.add(stream_id)
            cls._cancelled.discard(stream_id)
        try:
            task = asyncio.create_task(
                cls._wait_and_stream(command),
                name=f"ui-live-stream:{stream_id}",
            )
            task.add_done_callback(lambda completed: cls._done(stream_id, completed))
            async with cls._lock:
                cls._tasks[stream_id] = task
                cls._commands[stream_id] = dict(command)
            log.info(
                f"UI实时画面已进入运行页等待：stream={stream_id}，"
                f"type={command.get('execution_type')}，execution={command.get('execution_id')}"
            )
        finally:
            async with cls._lock:
                cls._starting.discard(stream_id)

    @classmethod
    async def _wait_and_stream(cls, command: dict) -> None:
        stream_id = command["stream_id"]
        execution_type = command.get("execution_type")
        execution_id = command.get("execution_id")
        is_workspace_stream = execution_type in {
            "element_workspace",
            "page_step_workspace",
        }
        # Case 允许先建立直播会话、稍后再点击执行，因此不能用固定的页面初始化超时。
        wait_timeout = None if execution_type == "ui_case" else (120 if is_workspace_stream else 30)
        try:
            log.debug(
                f"UI实时画面等待运行页面：stream={stream_id}，"
                f"type={execution_type}，execution={execution_id}，timeout={wait_timeout or '会话关闭'}"
            )
            runtime_state = await UiRuntimeRegistry.wait_for(
                execution_type,
                execution_id,
                timeout=wait_timeout,
            )
        except asyncio.TimeoutError as error:
            message = (
                f"等待UI实时画面运行页面超时：execution_type={execution_type}，"
                f"execution_id={execution_id}"
            )
            if is_workspace_stream:
                log.warning(f"{message}。工作区页面可能仍在初始化，前端会自动重连恢复。")
                return
            raise RuntimeError(message) from error
        except asyncio.CancelledError:
            log.info(
                f"UI实时画面等待已取消：stream={stream_id}，"
                f"type={execution_type}，execution={execution_id}"
            )
            raise

        display_url = getattr(runtime_state, "display_url", None)
        if not display_url:
            display_url = getattr(getattr(runtime_state, "page", None), "url", "-")
        log.debug(
            f"UI实时画面已获取运行页面：stream={stream_id}，url={display_url}"
        )
        async with cls._lock:
            if stream_id in cls._cancelled:
                log.debug(f"UI实时画面启动已取消：stream={stream_id}")
                return
            client = UiLiveStreamClient(runtime_state, command)
            cls._clients[stream_id] = client
        log.info(
            f"UI实时画面推流任务已启动：stream={stream_id}，"
            f"type={execution_type}，execution={execution_id}"
        )
        await client.run()

    @classmethod
    async def stop(cls, stream_id: str, reason: str | None = None) -> None:
        async with cls._lock:
            cls._cancelled.add(stream_id)
            client = cls._clients.pop(stream_id, None)
            task = cls._tasks.pop(stream_id, None)
            cls._commands.pop(stream_id, None)
        log.debug(
            f"UI实时画面停止：stream={stream_id}，"
            f"has_client={bool(client)}，has_task={bool(task)}"
        )
        if client:
            await client.stop(reason=reason)
        if task and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    @classmethod
    async def stop_execution(
            cls,
            execution_type: str,
            execution_id: str | int,
            reason: str | None = None,
    ) -> None:
        async with cls._lock:
            stream_ids = [
                stream_id
                for stream_id, command in cls._commands.items()
                if command.get("execution_type") == execution_type
                and str(command.get("execution_id")) == str(execution_id)
            ]
        for stream_id in stream_ids:
            await cls.stop(stream_id, reason=reason)

    @classmethod
    async def has_execution(cls, execution_type: str, execution_id: str | int) -> bool:
        async with cls._lock:
            return any(
                command.get("execution_type") == execution_type
                and str(command.get("execution_id")) == str(execution_id)
                for command in cls._commands.values()
            )

    @classmethod
    def _done(cls, stream_id: str, task: asyncio.Task) -> None:
        if cls._tasks.get(stream_id) is task:
            cls._tasks.pop(stream_id, None)
            cls._clients.pop(stream_id, None)
            cls._commands.pop(stream_id, None)
            cls._cancelled.discard(stream_id)
        if task.cancelled():
            return
        error = task.exception()
        if error:
            error_message = str(error) or type(error).__name__
            if "直播会话尚无观看者" in error_message:
                log.warning(f"UI实时画面发布端已关闭：stream_id={stream_id}，原因={error_message}")
                return
            log.warning(
                f"UI实时画面任务结束：stream_id={stream_id}, "
                f"类型：{type(error)}，详情：{error_message}，"
                f"明细：{''.join(traceback.format_exception(type(error), error, error.__traceback__))}"
            )
