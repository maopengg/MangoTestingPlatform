import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from mangoautomation.uidrives import AsyncWebRuntime, BaseData

from src.customization import ObtainAssertion, ObtainTestData
from mangotools.enums import DriveTypeEnum
from mangoautomation.models import DebugPageStepsModel
from src.services.runtime_config import get_ai_config
from src.services.ui.auth_cache import UiAuthCacheApplier
from src.services.runtime.session import AutomationSessionManager
from src.services.runtime.session.web_registry import WebContextRegistry
from src.services.ui.element_locator_engine import UiElementLocatorEngine
from src.services.ui.live_stream.environment import ensure_live_stream_supported
from src.services.ui.live_stream import UiLiveStreamManager, UiRuntimeRegistry
from src.services.ui.page_steps import PageSteps
from mangotools.enums import ClientTypeEnum
from src.network import ActuatorUiEventEnum, socket_conn
from src.tools import project_dir
from src.tools.log_collector import log
from src.tools.send_global_msg import send_global_msg


@dataclass
class UiLiveWorkspaceState:
    workspace_id: str
    workspace_type: str
    base_data: BaseData
    web_runtime: AsyncWebRuntime
    runtime_data: DebugPageStepsModel
    slot_id: str
    send_user: str | None
    last_activity_at: float
    auth_cache_signature: str = ""
    live_stream_count: int = 0
    running: bool = False
    operation_idle: asyncio.Event = field(default_factory=asyncio.Event)

    def __post_init__(self):
        self.operation_idle.set()


class UiLiveWorkspaceManager:
    MAX_USER_SLOTS = 5
    IDLE_TIMEOUT_SECONDS = 5 * 60
    WATCHDOG_INTERVAL_SECONDS = 5
    STOP_OPERATION_WAIT_SECONDS = 120
    _states: dict[str, UiLiveWorkspaceState] = {}
    _lock = asyncio.Lock()
    _start_locks: dict[str, asyncio.Lock] = {}
    _watchdog_task: asyncio.Task | None = None

    @classmethod
    async def start(cls, command: dict) -> None:
        ensure_live_stream_supported()
        workspace_id = str(command.get("workspace_id") or "")
        slot_id = str(command.get("slot_id") or workspace_id)
        if not workspace_id:
            raise RuntimeError("缺少UI实时工作区ID")
        try:
            await cls._ensure_watchdog()
            start_lock = await cls._start_lock(workspace_id)
            async with start_lock:
                await cls._ensure_slot_capacity(slot_id)
                runtime_data = DebugPageStepsModel(**(command.get("runtime_data") or {}))
                runtime_data.workspace_id = workspace_id
                runtime_data.slot_id = slot_id
                auth_cache_signature = cls._auth_cache_signature(runtime_data.ui_auth_cache)
                existing = await cls.get(workspace_id)
                if existing and cls._runtime_available(existing.base_data):
                    existing_signature = getattr(existing, "auth_cache_signature", None)
                    if existing_signature is None:
                        existing_signature = cls._auth_cache_signature(
                            getattr(existing.runtime_data, "ui_auth_cache", None)
                        )
                    if existing_signature == auth_cache_signature:
                        await cls.touch(workspace_id)
                        await UiRuntimeRegistry.register(
                            command.get("workspace_type"), workspace_id, existing.base_data
                        )
                        await cls._notify_status(command, "ready")
                        send_global_msg(f"UI实时工作区已复用：{existing.runtime_data.name}")
                        return
                    log.info(
                        f"UI实时工作区授权缓存已变化，将重建浏览器上下文：workspace={workspace_id}"
                    )
                await cls._stop_other_slot_workspace(slot_id, workspace_id)
                await cls.stop(workspace_id, reason="restart")
                web_runtime = AutomationSessionManager.web_runtime()
                base_data = AutomationSessionManager.create_base_data(runtime_data.test_env)
                setattr(base_data, "_runtime_session_id", workspace_id)
                setattr(base_data, "_web_owner_type", command.get("workspace_type") or "live_workspace")
                setattr(base_data, "_web_owner_id", workspace_id)
                setattr(base_data, "_web_purpose", "UI实时工作区")
                page_steps = PageSteps(base_data, web_runtime, runtime_data, True)
                await page_steps.driver_init()
                await UiAuthCacheApplier(base_data, web_runtime, runtime_data.ui_auth_cache).apply()
                await page_steps.page_init()
                if runtime_data.type == DriveTypeEnum.WEB.value and base_data.page:
                    target_url = page_steps._resolve_step_url()
                    log.debug(
                        f"UI实时工作区目标地址：workspace={workspace_id}，"
                        f"type={command.get('workspace_type') or ''}，url={target_url or '-'}，"
                        f"current={base_data.page.url or '-'}"
                    )
                    if target_url and base_data.page.url in ("about:blank", ""):
                        await base_data.page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
                    page_steps.test_object = base_data.page.url
                await UiRuntimeRegistry.register(command.get("workspace_type"), workspace_id, base_data)
                async with cls._lock:
                    cls._states[workspace_id] = UiLiveWorkspaceState(
                        workspace_id=workspace_id,
                        workspace_type=command.get("workspace_type") or "",
                        base_data=base_data,
                        web_runtime=web_runtime,
                        runtime_data=runtime_data,
                        slot_id=slot_id,
                        send_user=runtime_data.send_user,
                        last_activity_at=time.monotonic(),
                        auth_cache_signature=auth_cache_signature,
                    )
                await cls._notify_status(command, "ready")
                send_global_msg(f"UI实时工作区已打开：{runtime_data.name}")
        except Exception as error:
            await cls._notify_status(command, "failed", str(error) or type(error).__name__)
            raise

    @staticmethod
    async def _notify_status(command: dict, status: str, message: str = "") -> None:
        runtime_data = command.get("runtime_data") or {}
        try:
            await socket_conn.async_send(
                code=200 if status == "ready" else 300,
                msg="UI实时工作区准备完成" if status == "ready" else "UI实时工作区初始化失败",
                is_notice=ClientTypeEnum.WEB,
                user=runtime_data.get("send_user"),
                func_name=ActuatorUiEventEnum.LIVE_WORKSPACE_STATUS.value,
                func_args={
                    "workspace_id": str(command.get("workspace_id") or ""),
                    "status": status,
                    "message": message,
                    "slot_id": str(command.get("slot_id") or ""),
                    "idle_timeout_seconds": int(
                        command.get("idle_timeout_seconds") or UiLiveWorkspaceManager.IDLE_TIMEOUT_SECONDS
                    ),
                    "idle_deadline": command.get("idle_deadline"),
                },
                reliable=True,
            )
        except Exception as error:
            log.warning(
                f"UI实时工作区状态回传失败：workspace={command.get('workspace_id') or '-'}，"
                f"status={status}，error={type(error).__name__}"
            )

    @classmethod
    async def _start_lock(cls, workspace_id: str) -> asyncio.Lock:
        async with cls._lock:
            lock = cls._start_locks.get(workspace_id)
            if lock is None:
                lock = asyncio.Lock()
                cls._start_locks[workspace_id] = lock
            return lock

    @classmethod
    async def _stop_other_slot_workspace(cls, slot_id: str, workspace_id: str) -> None:
        async with cls._lock:
            other_workspace_ids = [
                current_workspace_id
                for current_workspace_id, state in cls._states.items()
                if current_workspace_id != str(workspace_id) and state.slot_id == slot_id
            ]
        for current_workspace_id in other_workspace_ids:
            await cls.stop(current_workspace_id, reason="same-slot-replaced")

    @classmethod
    async def _ensure_slot_capacity(cls, slot_id: str) -> None:
        async with cls._lock:
            active_slots = {state.slot_id for state in cls._states.values()}
        if slot_id not in active_slots and len(active_slots) >= cls.MAX_USER_SLOTS:
            raise RuntimeError(f"执行器当前已有 {len(active_slots)}/{cls.MAX_USER_SLOTS} 位用户使用")

    @classmethod
    async def stop(cls, workspace_id: str, reason: str = "closed") -> None:
        workspace_id = str(workspace_id)
        async with cls._lock:
            state = cls._states.get(workspace_id)
            if not state:
                cls._start_locks.pop(workspace_id, None)
        if not state:
            return
        if state.running:
            log.info(
                f"UI实时工作区正在执行操作，将在操作结束后关闭："
                f"workspace={workspace_id}，reason={reason}"
            )
            try:
                await asyncio.wait_for(
                    state.operation_idle.wait(),
                    timeout=cls.STOP_OPERATION_WAIT_SECONDS,
                )
            except asyncio.TimeoutError:
                log.warning(
                    f"等待UI实时工作区操作结束超时，将继续关闭："
                    f"workspace={workspace_id}，wait={cls.STOP_OPERATION_WAIT_SECONDS}s"
                )
        async with cls._lock:
            current_state = cls._states.get(workspace_id)
            if current_state is not state:
                return
            cls._states.pop(workspace_id, None)
        await UiLiveStreamManager.stop_execution(state.workspace_type, state.workspace_id)
        await UiRuntimeRegistry.unregister(state.workspace_type, state.workspace_id)
        try:
            await AutomationSessionManager.close_page_context(state.base_data, 'UI实时工作区')
        finally:
            async with cls._lock:
                cls._start_locks.pop(workspace_id, None)
            send_global_msg(f"UI实时工作区已关闭：{reason}")
            await cls._notify_closed(state, reason)

    @classmethod
    async def get(cls, workspace_id: str) -> UiLiveWorkspaceState | None:
        async with cls._lock:
            return cls._states.get(str(workspace_id))

    @staticmethod
    def _runtime_available(base_data: BaseData) -> bool:
        return WebContextRegistry.is_page_available(base_data.page) or base_data.ios is not None

    @staticmethod
    def _auth_cache_signature(auth_cache) -> str:
        if not auth_cache:
            return ""
        if hasattr(auth_cache, "model_dump"):
            auth_cache = auth_cache.model_dump(mode="json")
        payload = json.dumps(
            auth_cache,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    async def touch(cls, workspace_id: str) -> None:
        async with cls._lock:
            state = cls._states.get(str(workspace_id))
            if state:
                state.last_activity_at = time.monotonic()

    @classmethod
    async def set_live(cls, workspace_id: str, active: bool) -> None:
        async with cls._lock:
            state = cls._states.get(str(workspace_id))
            if state:
                state.live_stream_count = max(0, state.live_stream_count + (1 if active else -1))
                state.last_activity_at = time.monotonic()

    @classmethod
    async def set_running(cls, workspace_id: str, running: bool) -> None:
        async with cls._lock:
            state = cls._states.get(str(workspace_id))
            if state:
                state.running = bool(running)
                if state.running:
                    state.operation_idle.clear()
                else:
                    state.operation_idle.set()
                state.last_activity_at = time.monotonic()

    @classmethod
    async def _ensure_watchdog(cls) -> None:
        if cls._watchdog_task and not cls._watchdog_task.done():
            return
        cls._watchdog_task = asyncio.create_task(cls._watchdog(), name="ui-live-workspace-idle-watchdog")

    @classmethod
    async def _watchdog(cls) -> None:
        while True:
            await asyncio.sleep(cls.WATCHDOG_INTERVAL_SECONDS)
            expired = await cls.expired_workspace_ids()
            for workspace_id in expired:
                await cls.stop(workspace_id, reason="idle-timeout")

    @classmethod
    async def expired_workspace_ids(cls, now: float | None = None) -> list[str]:
        current = time.monotonic() if now is None else now
        async with cls._lock:
            return [
                state.workspace_id
                for state in cls._states.values()
                if not state.running
                and state.live_stream_count <= 0
                and current - state.last_activity_at >= cls.IDLE_TIMEOUT_SECONDS
            ]

    @staticmethod
    async def _notify_closed(state: UiLiveWorkspaceState, reason: str) -> None:
        if not state.send_user:
            return
        try:
            await socket_conn.async_send(
                code=200,
                msg="UI实时工作区已关闭",
                is_notice=ClientTypeEnum.WEB,
                user=state.send_user,
                func_name=ActuatorUiEventEnum.LIVE_WORKSPACE_STATUS.value,
                func_args={
                    "workspace_id": state.workspace_id,
                    "status": "closed",
                    "message": "超过5分钟无操作，浏览器已自动关闭" if reason == "idle-timeout" else "",
                    "reason": reason,
                    "slot_id": state.slot_id,
                },
                reliable=True,
            )
        except Exception as error:
            log.warning(
                f"UI实时工作区关闭状态回传失败：workspace={state.workspace_id}，"
                f"error={type(error).__name__}"
            )

    @classmethod
    async def wait_for(cls, workspace_id: str, timeout: float = 120) -> UiLiveWorkspaceState | None:
        workspace_id = str(workspace_id or "")
        if not workspace_id:
            return None
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while loop.time() < deadline:
            state = await cls.get(workspace_id)
            if state and cls._runtime_available(state.base_data):
                return state
            await asyncio.sleep(0.1)
        return None
