from mangoautomation.uidrives import AsyncWebRuntime, BaseData

from src.services.runtime.session.android_session import AndroidDevicePool
from src.services.runtime.session.base import RuntimeBaseDataFactory
from src.services.runtime.session.case_session import CaseRuntimeSession
from src.services.runtime.session.close_utils import RuntimeCloseUtils
from src.services.runtime.session.web_registry import WebContextRegistry
from src.services.runtime.session.web_session import WebSessionManager


class AutomationSessionManager:
    @classmethod
    def web_runtime(cls) -> AsyncWebRuntime:
        return WebSessionManager.runtime()

    @classmethod
    def reset_web_runtime(cls) -> AsyncWebRuntime:
        return WebSessionManager.reset_runtime()

    @classmethod
    def create_web_runtime(cls) -> AsyncWebRuntime:
        return cls.web_runtime()

    @classmethod
    async def ensure_web_page(
        cls,
        base_data: BaseData,
        web_runtime: AsyncWebRuntime | None = None,
        owner_type: str = "unknown",
        owner_id: str | int | None = None,
        purpose: str | None = None,
    ):
        web_runtime = web_runtime or cls.web_runtime()
        if web_runtime.browser and not web_runtime.browser.is_connected():
            web_runtime.browser = None
            WebContextRegistry.unregister_base(base_data, "browser-disconnected")
            base_data.context = None
            base_data.page = None
        if WebContextRegistry.is_page_available(base_data.page) and base_data.context is not None:
            WebContextRegistry.touch(base_data)
            return base_data.context, base_data.page
        WebContextRegistry.unregister_base(base_data, "recreate-page")
        base_data.context = None
        base_data.page = None
        context, page = await web_runtime.new_context_page()
        base_data.bind_web(web_runtime, context=context, page=page)
        WebContextRegistry.bind(
            base_data,
            web_runtime,
            context,
            page,
            owner_type=owner_type,
            owner_id=owner_id,
            purpose=purpose,
        )
        return context, page

    @classmethod
    def create_base_data(cls, test_env: int | None = None, test_data=None) -> BaseData:
        return RuntimeBaseDataFactory.create(test_env, test_data)

    @classmethod
    def create_case_session(
        cls,
        session_id: str,
        base_data: BaseData,
    ) -> CaseRuntimeSession:
        return CaseRuntimeSession(
            session_id=session_id,
            base_data=base_data,
        )

    @classmethod
    async def close_page_context(cls, base_data: BaseData | None, reason: str = "") -> None:
        await RuntimeCloseUtils.close_page_context(base_data, reason)

    @classmethod
    async def close_browser(cls) -> None:
        await WebSessionManager.close_browser()

    @classmethod
    def web_runtime_snapshot(cls) -> dict:
        return WebContextRegistry.snapshot(cls.web_runtime())

    @classmethod
    async def close_idle_web_contexts(cls, idle_seconds: int = 1800) -> int:
        return await WebContextRegistry.close_idle(idle_seconds)

    @classmethod
    async def acquire_android(
        cls,
        base_data: BaseData,
        equipment: str,
        package_name: str | None,
        owner: str,
    ):
        return await AndroidDevicePool.acquire(base_data, equipment, package_name, owner)

    @classmethod
    async def release_android(cls, equipment: str | None = None, owner: str | None = None) -> None:
        await AndroidDevicePool.release(equipment, owner)

    @classmethod
    async def acquire_ios(cls, base_data: BaseData, server_url: str, capabilities: dict, owner: str):
        try:
            from src.services.runtime.session.ios_session import IOSDevicePool
        except (ImportError, ModuleNotFoundError) as error:
            raise RuntimeError(
                '当前执行器未安装 iOS 自动化组件，请选择 iOS 执行器后再试'
            ) from error
        return await IOSDevicePool.acquire(base_data, server_url, capabilities, owner)

    @classmethod
    async def release_ios(cls, equipment: str | None = None, owner: str | None = None) -> None:
        try:
            from src.services.runtime.session.ios_session import IOSDevicePool
        except (ImportError, ModuleNotFoundError):
            return
        await IOSDevicePool.release(equipment, owner)
