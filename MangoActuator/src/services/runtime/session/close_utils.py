from mangoautomation.uidrives import BaseData

from src.services.runtime.session.web_registry import WebContextRegistry
from src.tools.log_collector import log


class RuntimeCloseUtils:
    @staticmethod
    async def close_page_context(base_data: BaseData | None, reason: str = "") -> None:
        if not base_data:
            return
        prefix = f"[资源关闭] {reason} " if reason else "[资源关闭] "
        WebContextRegistry.unregister_base(base_data, reason or "close-page-context")
        try:
            page = base_data.page
            if page:
                try:
                    if hasattr(page, "is_closed") and page.is_closed():
                        page = None
                except Exception:
                    pass
            if page:
                await page.close()
                log.debug(f"{prefix}Page已关闭")
        except Exception as error:
            log.warning(f"{prefix}Page关闭失败，类型：{type(error)}，失败详情：{error}")
        try:
            if base_data.context:
                await base_data.context.close()
                log.debug(f"{prefix}Context已关闭")
        except Exception as error:
            log.warning(f"{prefix}Context关闭失败，类型：{type(error)}，失败详情：{error}")
        try:
            owner = getattr(base_data, "_runtime_session_id", None)
            equipment = getattr(base_data, "_android_equipment", None)
            if equipment:
                from src.services.runtime.session.android_session import AndroidDevicePool
                await AndroidDevicePool.release(equipment, owner=owner)
        except Exception as error:
            log.warning(f"{prefix}Android租约释放失败，类型：{type(error)}，失败详情：{error}")
        try:
            owner = getattr(base_data, "_runtime_session_id", None)
            equipment = getattr(base_data, "_ios_equipment", None)
            if equipment:
                from src.services.runtime.session.ios_session import IOSDevicePool
                await IOSDevicePool.release(equipment, owner=owner)
        except Exception as error:
            log.warning(f"{prefix}iOS租约释放失败，类型：{type(error)}，失败详情：{error}")
        base_data.setup()
