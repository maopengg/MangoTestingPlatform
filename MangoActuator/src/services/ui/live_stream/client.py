from src.services.system_error_reporter import ActuatorSystemErrorReporter
import asyncio
import json
from contextlib import suppress
from urllib.parse import quote

from mangotools.data_processor import SqlCache
from websockets.legacy.client import connect as websocket_connect
from websockets.exceptions import ConnectionClosedOK

from src.enums.tools_enum import CacheKeyEnum
from src.services.ui.live_stream.capture import LatestFrameBuffer, PlaywrightFrameCapture
from src.services.ui.live_stream.control import RemoteControlExecutor
from src.services.ui.live_stream.runtime_registry import UiRuntimeRegistry
from src.tools import project_dir
from src.tools.log_collector import log


class UiLiveStreamClient:
    CONTROL_EVENT_TIMEOUT_SECONDS = 2.5
    CONTROL_COMMAND_TIMEOUT_SECONDS = 14.0
    SCAN_COMMAND_TIMEOUT_SECONDS = 44.0
    LONG_RUNNING_CONTROL_EVENTS = {"pick_element", "check_locator"}

    def __init__(self, runtime_state, command: dict):
        self.runtime_state = runtime_state
        self.command = command
        self.stream_id = command["stream_id"]
        self.running = True
        self.buffer = LatestFrameBuffer()
        self.capture = PlaywrightFrameCapture(runtime_state, command.get("config") or {}, self.buffer)
        self.control = RemoteControlExecutor(runtime_state)
        self._control_lease_task: asyncio.Task | None = None
        self._websocket = None
        # 视频帧、控制回执和状态消息共用发布连接。legacy websockets 在
        # 发生发送背压时不允许多个协程同时 drain，否则会触发内部断言。
        self._send_lock = asyncio.Lock()

    async def run(self) -> None:
        websocket_base_url = str(
            SqlCache(project_dir.cache_file()).get_sql_cache(CacheKeyEnum.WS.value)
        ).rstrip("/")
        url = (
            f"{websocket_base_url}{self.command['publish_path']}"
            f"?token={quote(self.command['publish_token'], safe='')}"
        )
        tasks: list[asyncio.Task] = []
        try:
            await self._set_workspace_live(True)
            log.info(
                f"UI实时画面连接推流通道：stream={self.stream_id}，"
                f"url={url.split('?')[0]}，page={self.runtime_state.display_url}"
            )
            async with websocket_connect(
                url,
                max_size=3 * 1024 * 1024,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=5,
            ) as websocket:
                self._websocket = websocket
                ready = json.loads(await asyncio.wait_for(websocket.recv(), timeout=10))
                if ready.get("type") != "publisher_ready":
                    raise RuntimeError(ready.get("message") or "实时画面发布连接失败")
                log.info(
                    f"UI实时画面推流通道已就绪：stream={self.stream_id}，"
                    f"page={self.runtime_state.display_url}"
                )
                await self._send(websocket, json.dumps({
                    "type": "stream_status",
                    "status": "streaming",
                    "page_url": self.runtime_state.display_url,
                }, ensure_ascii=False))
                tasks = [
                    asyncio.create_task(self.capture.run(), name=f"live-capture:{self.stream_id}"),
                    asyncio.create_task(self._send_frames(websocket), name=f"live-send:{self.stream_id}"),
                    asyncio.create_task(self._receive_control(websocket), name=f"live-control:{self.stream_id}"),
                ]
                try:
                    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                    for task in pending:
                        task.cancel()
                    await asyncio.gather(*pending, return_exceptions=True)
                    for task in done:
                        task.result()
                finally:
                    self._websocket = None
                    self.capture.stop()
                    self.running = False
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    if tasks:
                        await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            await self._set_workspace_live(False)
            self.running = False
            self.capture.stop()
            await self._stop_control()
            await UiRuntimeRegistry.resume_automation(self.runtime_state)
            log.info(f"UI实时画面客户端已停止：stream={self.stream_id}")

    async def stop(self, reason: str | None = None) -> None:
        websocket = self._websocket
        if reason and websocket is not None:
            with suppress(Exception):
                await self._send(websocket, json.dumps({
                    "type": "stream_status",
                    "status": "completed",
                    "reason": reason,
                    "message": "Case执行完成，实时画面已正常结束",
                }, ensure_ascii=False))
        self.running = False
        self.capture.stop()

    async def _send_frames(self, websocket) -> None:
        frame_count = 0
        with suppress(ConnectionClosedOK):
            while self.running:
                await self._send(websocket, await self.buffer.get())
                frame_count += 1
                if frame_count == 1:
                    log.info(f"UI实时画面已发送第一帧：stream={self.stream_id}")

    async def _receive_control(self, websocket) -> None:
        with suppress(ConnectionClosedOK):
            while self.running:
                payload = json.loads(await websocket.recv())
                event_type = payload.get("type")
                if event_type == "stop_capture":
                    self.running = False
                    self.capture.stop()
                    return
                if event_type == "control_started":
                    await UiRuntimeRegistry.pause_automation(self.runtime_state)
                    self._reset_control_lease(float(payload.get("lease_seconds") or 30))
                elif event_type == "control_stopped":
                    await self._stop_control()
                elif event_type == "control_event":
                    event = payload.get("data") or {}
                    await self._execute_control_event(websocket, event)

    async def _execute_control_event(self, websocket, event: dict) -> None:
        await self._touch_workspace()
        event_type = str(event.get("event_type") or "")
        if event_type in self.LONG_RUNNING_CONTROL_EVENTS:
            timeout_seconds = self.CONTROL_COMMAND_TIMEOUT_SECONDS
        else:
            timeout_seconds = self.CONTROL_EVENT_TIMEOUT_SECONDS
        try:
            result = await asyncio.wait_for(
                self.control.execute(event),
                timeout=timeout_seconds,
            )
            payload = {
                "type": "control_ack",
                "sequence": event.get("sequence"),
                "success": True,
                "data": result,
            }
        except asyncio.TimeoutError:
            payload = {
                "type": "control_ack",
                "sequence": event.get("sequence"),
                "success": False,
                "message": f"实时控制执行超时，操作已放弃：{event_type}",
            }
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'services/ui/live_stream/client:_execute_control_event')
            payload = {
                "type": "control_ack",
                "sequence": event.get("sequence"),
                "success": False,
                "message": str(error),
            }
        await self._send(websocket, json.dumps(payload, ensure_ascii=False))

    async def _send(self, websocket, payload) -> None:
        async with self._send_lock:
            await websocket.send(payload)

    async def _touch_workspace(self) -> None:
        if self.command.get("execution_type") not in {"element_workspace", "page_step_workspace"}:
            return
        from src.services.ui.live_workspace import UiLiveWorkspaceManager

        await UiLiveWorkspaceManager.touch(str(self.command.get("execution_id") or ""))

    async def _set_workspace_live(self, active: bool) -> None:
        if self.command.get("execution_type") not in {"element_workspace", "page_step_workspace"}:
            return
        from src.services.ui.live_workspace import UiLiveWorkspaceManager

        await UiLiveWorkspaceManager.set_live(
            str(self.command.get("execution_id") or ""),
            active,
        )

    def _reset_control_lease(self, lease_seconds: float) -> None:
        if self._control_lease_task:
            self._control_lease_task.cancel()
        self._control_lease_task = asyncio.create_task(
            self._control_lease_timeout(max(1, lease_seconds + 3)),
            name=f"ui-live-control-lease:{self.stream_id}",
        )

    async def _control_lease_timeout(self, timeout: float) -> None:
        await asyncio.sleep(timeout)
        await self._stop_control(cancel_timer=False)

    async def _stop_control(self, cancel_timer: bool = True) -> None:
        task = self._control_lease_task
        self._control_lease_task = None
        if cancel_timer and task and task is not asyncio.current_task():
            task.cancel()
        await self.control.release_all()
        await UiRuntimeRegistry.resume_automation(self.runtime_state)
