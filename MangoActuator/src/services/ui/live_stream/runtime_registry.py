from src.services.system_error_reporter import ActuatorSystemErrorReporter
import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any


@dataclass
class UiRuntimeState:
    execution_type: str
    execution_id: str
    base_data: Any
    operation_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    automation_allowed: asyncio.Event = field(default_factory=asyncio.Event)
    selected_scan_region: dict | None = None
    selected_scan_region_page: Any = None

    def __post_init__(self):
        self.automation_allowed.set()

    @property
    def page(self):
        return self.base_data.page

    @property
    def ios(self):
        return getattr(self.base_data, 'ios', None)

    @property
    def display_url(self):
        if self.page is not None:
            return getattr(self.page, 'url', '-')
        return f"ios://{getattr(self.base_data, 'bundle_id', '') or 'session'}"


class UiRuntimeRegistry:
    _states: dict[tuple[str, str], UiRuntimeState] = {}
    _page_states: dict[int, UiRuntimeState] = {}
    _condition = asyncio.Condition()

    @staticmethod
    def _is_page_available(page) -> bool:
        if page is None:
            return False
        try:
            return not page.is_closed()
        except Exception as _unexpected_error:
            ActuatorSystemErrorReporter.schedule(_unexpected_error, 'services/ui/live_stream/runtime_registry:_is_page_available')
            return False

    @classmethod
    def _is_runtime_available(cls, state: UiRuntimeState) -> bool:
        return cls._is_page_available(state.page) or state.ios is not None

    @classmethod
    async def register(cls, execution_type: str, execution_id: str | int, base_data) -> UiRuntimeState:
        key = (execution_type, str(execution_id))
        async with cls._condition:
            state = cls._states.get(key)
            if state is None:
                state = UiRuntimeState(execution_type, str(execution_id), base_data)
                cls._states[key] = state
            else:
                state.base_data = base_data
            if cls._is_page_available(base_data.page):
                cls._page_states[id(base_data.page)] = state
            cls._condition.notify_all()
            return state

    @classmethod
    async def register_alias(
        cls,
        execution_type: str,
        execution_id: str | int,
        state: UiRuntimeState,
    ) -> None:
        key = (execution_type, str(execution_id))
        async with cls._condition:
            cls._states[key] = state
            if cls._is_page_available(state.page):
                cls._page_states[id(state.page)] = state
            cls._condition.notify_all()

    @classmethod
    async def unregister(cls, execution_type: str, execution_id: str | int) -> None:
        key = (execution_type, str(execution_id))
        async with cls._condition:
            state = cls._states.pop(key, None)
            if state and state not in cls._states.values():
                cls._page_states = {
                    page_id: item for page_id, item in cls._page_states.items() if item is not state
                }
                state.automation_allowed.set()
            cls._condition.notify_all()

    @classmethod
    async def set_active_page(cls, state: UiRuntimeState, page) -> None:
        async with cls._condition:
            state.base_data.page = page
            if cls._is_page_available(page):
                cls._page_states[id(page)] = state
            cls._condition.notify_all()

    @classmethod
    async def wait_for(
        cls,
        execution_type: str,
        execution_id: str | int,
        timeout: float | None = 30,
    ) -> UiRuntimeState:
        key = (execution_type, str(execution_id))

        async def wait_until_available():
            async with cls._condition:
                while key not in cls._states or not cls._is_runtime_available(cls._states[key]):
                    if key in cls._states and not cls._is_runtime_available(cls._states[key]):
                        cls._page_states = {
                            page_id: item
                            for page_id, item in cls._page_states.items()
                            if item is not cls._states[key]
                        }
                    await cls._condition.wait()
                return cls._states[key]

        return await asyncio.wait_for(wait_until_available(), timeout=timeout)

    @classmethod
    async def pause_automation(cls, state: UiRuntimeState) -> None:
        state.automation_allowed.clear()

    @classmethod
    async def resume_automation(cls, state: UiRuntimeState) -> None:
        state.automation_allowed.set()

    @classmethod
    @asynccontextmanager
    async def operation_guard(cls, runtime_target):
        state = cls._page_states.get(id(runtime_target)) if runtime_target else None
        if state is None and runtime_target:
            state = next(
                (
                    item
                    for item in cls._states.values()
                    if item.page is runtime_target or item.ios is runtime_target
                ),
                None,
            )
            if state:
                cls._page_states[id(runtime_target)] = state
        if state is None:
            yield
            return
        while True:
            await state.automation_allowed.wait()
            await state.operation_lock.acquire()
            if state.automation_allowed.is_set():
                break
            state.operation_lock.release()
        try:
            yield
        finally:
            state.operation_lock.release()
