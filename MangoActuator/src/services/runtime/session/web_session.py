import asyncio

from mangoautomation.uidrives import AsyncWebRuntime, WebDriverFactory

from src.tools import project_dir
from src.tools.log_collector import log
from src.tools.set_config import SetConfig
from src.services.runtime.session.web_registry import WebContextRegistry


class WebSessionManager:
    _runtime: AsyncWebRuntime | None = None
    _lock = asyncio.Lock()

    @classmethod
    def runtime(cls) -> AsyncWebRuntime:
        if cls._runtime is None:
            cls._runtime = cls._create_runtime()
        return cls._runtime

    @classmethod
    def reset_runtime(cls) -> AsyncWebRuntime:
        WebContextRegistry.clear("reset-runtime")
        cls._runtime = cls._create_runtime()
        return cls._runtime

    @staticmethod
    def _create_runtime() -> AsyncWebRuntime:
        web_max = SetConfig.get_web_max()  # type: ignore
        web_headers = SetConfig.get_web_headers()  # type: ignore
        web_recording = SetConfig.get_web_recording()  # type: ignore
        web_h5 = SetConfig.get_web_h5()  # type: ignore
        log.info("[驱动初始化] 初始化Web runtime (异步模式: True)")
        return WebDriverFactory.create_async_runtime(
            web_type=SetConfig.get_web_type(),  # type: ignore
            web_path=SetConfig.get_web_path(),  # type: ignore
            web_max=web_max if web_max else False,
            web_headers=web_headers if web_headers else False,
            web_recording=web_recording if web_recording else False,
            web_h5=web_h5 if web_h5 and web_h5 != "None" else None,
            web_is_default=SetConfig.get_web_default(),  # type: ignore
            videos_path=project_dir.videos(),
            static_cache_enabled=bool(SetConfig.get_web_static_cache_enabled()),  # type: ignore
            static_cache_path=SetConfig.get_web_static_cache_path(),  # type: ignore
            log=log,
        )

    @classmethod
    async def close_browser(cls) -> None:
        async with cls._lock:
            runtime = cls._runtime
            cls._runtime = None
            WebContextRegistry.clear("close-browser")
        if runtime:
            await runtime.close()
