import time
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any

from mangoautomation.uidrives import AsyncWebRuntime, BaseData

from src.tools.log_collector import log


@dataclass
class WebPageLease:
    lease_id: str
    owner_type: str
    owner_id: str
    purpose: str
    context_id: int
    page_id: int
    created_time: str
    last_active_time: str
    created_ts: float
    last_active_ts: float
    url: str = ""
    status: str = "active"

    def to_dict(self) -> dict:
        return asdict(self)


class WebContextRegistry:
    _leases_by_context: dict[int, WebPageLease] = {}
    _leases_by_page: dict[int, WebPageLease] = {}
    _contexts: dict[int, Any] = {}
    _pages: dict[int, Any] = {}

    @classmethod
    def bind(
        cls,
        base_data: BaseData,
        runtime: AsyncWebRuntime,
        context: Any,
        page: Any,
        owner_type: str,
        owner_id: str | int | None,
        purpose: str | None = None,
    ) -> WebPageLease:
        now = time.time()
        owner_id = str(owner_id or f"base:{id(base_data)}")
        owner_type = owner_type or "unknown"
        purpose = purpose or owner_type
        lease = WebPageLease(
            lease_id=f"{owner_type}:{owner_id}:{id(context)}:{id(page)}",
            owner_type=owner_type,
            owner_id=owner_id,
            purpose=purpose,
            context_id=id(context),
            page_id=id(page),
            created_time=cls._format_time(now),
            last_active_time=cls._format_time(now),
            created_ts=now,
            last_active_ts=now,
            url=getattr(page, "url", "") or "",
        )
        cls._leases_by_context[id(context)] = lease
        cls._leases_by_page[id(page)] = lease
        cls._contexts[id(context)] = context
        cls._pages[id(page)] = page
        cls._set_base_metadata(base_data, runtime, lease)
        cls._attach_close_hooks(context, page)
        log.debug(
            f"[Web会话] 已绑定页面租约：owner={lease.owner_type}/{lease.owner_id}，"
            f"purpose={lease.purpose}，context={lease.context_id}，page={lease.page_id}"
        )
        return lease

    @classmethod
    def touch(cls, base_data: BaseData | None) -> None:
        lease = cls.get_by_base(base_data)
        if not lease:
            return
        now = time.time()
        lease.last_active_ts = now
        lease.last_active_time = cls._format_time(now)
        page = getattr(base_data, "page", None)
        lease.url = getattr(page, "url", "") or lease.url
        lease.status = "active"

    @classmethod
    def get_by_base(cls, base_data: BaseData | None) -> WebPageLease | None:
        if not base_data:
            return None
        page = getattr(base_data, "page", None)
        context = getattr(base_data, "context", None)
        if page:
            lease = cls._leases_by_page.get(id(page))
            if lease:
                return lease
        if context:
            return cls._leases_by_context.get(id(context))
        lease_id = getattr(base_data, "_web_lease_id", None)
        if lease_id:
            return next((item for item in cls._leases_by_context.values() if item.lease_id == lease_id), None)
        return None

    @classmethod
    def unregister_base(cls, base_data: BaseData | None, reason: str = "") -> None:
        if not base_data:
            return
        page = getattr(base_data, "page", None)
        context = getattr(base_data, "context", None)
        cls.unregister(context=context, page=page, reason=reason)
        for attr in (
            "_web_lease_id",
            "_web_owner_type",
            "_web_owner_id",
            "_web_purpose",
            "_web_runtime",
        ):
            if hasattr(base_data, attr):
                try:
                    delattr(base_data, attr)
                except Exception:
                    pass

    @classmethod
    def unregister(cls, context: Any = None, page: Any = None, reason: str = "") -> None:
        lease = None
        if page:
            lease = cls._leases_by_page.pop(id(page), None)
        if context:
            lease = cls._leases_by_context.pop(id(context), None) or lease
        if not lease:
            return
        cls._drop_lease(lease, reason)

    @classmethod
    def unregister_lease(cls, lease: WebPageLease, reason: str = "") -> None:
        cls._drop_lease(lease, reason)

    @classmethod
    def _drop_lease(cls, lease: WebPageLease, reason: str = "") -> None:
        if lease:
            cls._leases_by_page.pop(lease.page_id, None)
            cls._leases_by_context.pop(lease.context_id, None)
            cls._pages.pop(lease.page_id, None)
            cls._contexts.pop(lease.context_id, None)
            lease.status = "closed"
            log.debug(
                f"[Web会话] 已注销页面租约：owner={lease.owner_type}/{lease.owner_id}，"
                f"purpose={lease.purpose}，reason={reason or '-'}"
            )

    @classmethod
    def snapshot(cls, runtime: AsyncWebRuntime | None = None) -> dict:
        browser = getattr(runtime, "browser", None) if runtime else None
        browser_connected = False
        browser_context_count = 0
        if browser:
            try:
                browser_connected = browser.is_connected()
            except Exception:
                browser_connected = False
            try:
                browser_context_count = len(getattr(browser, "contexts", []) or [])
            except Exception:
                browser_context_count = 0
        leases = [lease.to_dict() for lease in cls._leases_by_context.values()]
        return {
            "browser_exists": bool(browser),
            "browser_connected": browser_connected,
            "browser_context_count": browser_context_count,
            "tracked_context_count": len(cls._leases_by_context),
            "tracked_page_count": len(cls._leases_by_page),
            "leases": leases,
        }

    @classmethod
    def clear(cls, reason: str = "") -> None:
        count = len(cls._leases_by_context)
        cls._leases_by_context.clear()
        cls._leases_by_page.clear()
        cls._contexts.clear()
        cls._pages.clear()
        log.debug(f"[Web会话] 已清空页面租约：count={count}，reason={reason or '-'}")

    @classmethod
    async def close_idle(cls, idle_seconds: int) -> int:
        now = time.time()
        closed_count = 0
        leases = list(cls._leases_by_context.values())
        for lease in leases:
            if now - lease.last_active_ts < idle_seconds:
                continue
            context = cls._find_context_by_id(lease.context_id)
            if not context:
                cls.unregister_lease(lease, reason="idle-missing-context")
                continue
            try:
                await context.close()
                closed_count += 1
            except Exception as error:
                log.warning(f"[Web会话] 关闭闲置Context失败：lease={lease.lease_id}，错误={error}")
            finally:
                cls.unregister(context=context, reason=f"idle>{idle_seconds}s")
        return closed_count

    @staticmethod
    def is_page_available(page: Any) -> bool:
        if not page:
            return False
        try:
            return not page.is_closed()
        except Exception:
            return False

    @staticmethod
    def _format_time(ts: float) -> str:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def _set_base_metadata(
        cls,
        base_data: BaseData,
        runtime: AsyncWebRuntime,
        lease: WebPageLease,
    ) -> None:
        setattr(base_data, "_web_lease_id", lease.lease_id)
        setattr(base_data, "_web_owner_type", lease.owner_type)
        setattr(base_data, "_web_owner_id", lease.owner_id)
        setattr(base_data, "_web_purpose", lease.purpose)
        setattr(base_data, "_web_runtime", runtime)

    @classmethod
    def _attach_close_hooks(cls, context: Any, page: Any) -> None:
        try:
            page.on("close", lambda: cls.unregister(page=page, reason="page-close-event"))
        except Exception:
            pass
        try:
            context.on("close", lambda: cls.unregister(context=context, reason="context-close-event"))
        except Exception:
            pass

    @classmethod
    def _find_context_by_id(cls, context_id: int):
        return cls._contexts.get(context_id)
