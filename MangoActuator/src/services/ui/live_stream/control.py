import time
import asyncio

from mangoautomation.uidrives.web import WebElementInspector, WebStepRecorder

from src.services.ui.live_stream.runtime_registry import UiRuntimeRegistry
from src.tools.log_collector import log


class RemoteControlExecutor:
    """直播命令调度和平台结果适配；通用浏览器检查能力由 mangoautomation 提供。"""

    ALLOWED_BUTTONS = {"left", "right", "middle"}

    def __init__(self, runtime_state):
        self.runtime_state = runtime_state
        self.inspector = WebElementInspector() if getattr(runtime_state, "ios", None) is None else None
        self.recorder = WebStepRecorder(self.inspector) if self.inspector else None
        self.pressed_buttons: set[str] = set()
        self.pressed_keys: set[str] = set()

    async def execute(self, event: dict) -> dict | None:
        event_type = event.get("event_type")
        if getattr(self.runtime_state, "ios", None) is not None:
            return await self._execute_ios(event_type, event)
        if event_type == "list_pages":
            return await self._list_pages()
        if event_type == "switch_page":
            return await self._switch_page(event)
        if event_type == "close_page":
            return await self._close_page(event)
        page = self.runtime_state.page
        if page is None or page.is_closed():
            raise RuntimeError("远程控制目标页面已关闭")
        async with self.runtime_state.operation_lock:
            if event_type == "mouse_move":
                x, y = await self._event_coordinates(page, event)
                await page.mouse.move(x, y)
            elif event_type == "mouse_click":
                viewport = await self._viewport_size(page)
                x, y = self._coordinates_from_viewport(event, viewport)
                button = self._button(event)
                log.debug(
                    f"UI直播远程点击：x={round(x, 2)}, y={round(y, 2)}, "
                    f"button={button}, viewport={viewport}"
                )
                await page.mouse.click(
                    x,
                    y,
                    button=button,
                    click_count=min(int(event.get("click_count", 1)), 2),
                )
            elif event_type == "mouse_down":
                x, y = await self._event_coordinates(page, event)
                button = self._button(event)
                await page.mouse.move(x, y)
                await page.mouse.down(button=button)
                self.pressed_buttons.add(button)
            elif event_type == "mouse_up":
                x, y = await self._event_coordinates(page, event)
                button = self._button(event)
                await page.mouse.move(x, y)
                await page.mouse.up(button=button)
                self.pressed_buttons.discard(button)
            elif event_type == "mouse_wheel":
                if "x" in event or "y" in event:
                    x, y = await self._event_coordinates(page, event)
                    await page.mouse.move(x, y)
                await page.mouse.wheel(
                    float(event.get("delta_x", 0)),
                    float(event.get("delta_y", 0)),
                )
            elif event_type == "keyboard_press":
                await page.keyboard.press(self._key(event))
            elif event_type == "keyboard_down":
                key = self._key(event)
                await page.keyboard.down(key)
                self.pressed_keys.add(key)
            elif event_type == "keyboard_up":
                key = self._key(event)
                await page.keyboard.up(key)
                self.pressed_keys.discard(key)
            elif event_type == "text_input":
                await page.keyboard.insert_text(str(event.get("text", ""))[:2000])
            elif event_type == "pick_element":
                x, y = await self._event_coordinates(page, event)
                return await self._pick_element(page, x, y)
            elif event_type == "check_locator":
                return await self._check_locator(page, event)
            elif event_type == "record_action":
                return {"recorded_action": await self.recorder.execute(page, event)}
            elif event_type == "record_poll":
                return {"passive_actions": await self.recorder.poll_passive_events(page)}
            else:
                raise RuntimeError(f"不支持的远程控制事件：{event_type or '-'}")
        return None

    async def _execute_ios(self, event_type: str | None, event: dict) -> dict | None:
        driver = getattr(self.runtime_state, "ios", None)
        if driver is None:
            raise RuntimeError("iOS实时控制目标会话已关闭")
        async with self.runtime_state.operation_lock:
            if event_type == "list_pages":
                return {
                    "pages": [{
                        "page_id": "ios",
                        "index": 0,
                        "title": getattr(self.runtime_state.base_data, "bundle_id", "") or "iOS应用",
                        "url": getattr(self.runtime_state, "display_url", "ios://session"),
                        "active": True,
                    }]
                }
            if event_type in {"switch_page", "close_page"}:
                raise RuntimeError("iOS应用不支持浏览器页签操作")
            if event_type == "mouse_click":
                x, y = await self._ios_coordinates(driver, event)
                await asyncio.to_thread(
                    driver.execute_script,
                    "mobile: tap",
                    {"x": x, "y": y},
                )
                return None
            if event_type == "mouse_wheel":
                direction = self._ios_swipe_direction(event)
                await asyncio.to_thread(
                    driver.execute_script,
                    "mobile: swipe",
                    {"direction": direction},
                )
                return None
            if event_type == "text_input":
                text = str(event.get("text", ""))[:2000]
                element = await asyncio.to_thread(lambda: driver.switch_to.active_element)
                await asyncio.to_thread(element.send_keys, text)
                return None
            if event_type == "keyboard_press":
                key = self._key(event)
                if key not in {"Home", "home"}:
                    raise RuntimeError("iOS实时控制当前仅支持Home按键")
                await asyncio.to_thread(
                    driver.execute_script,
                    "mobile: pressButton",
                    {"name": "home"},
                )
                return None
            if event_type in {"mouse_move", "mouse_down", "mouse_up"}:
                return None
            if event_type in {"pick_element", "check_locator", "record_action", "record_poll"}:
                raise RuntimeError("iOS第一版暂不支持直播采集和录制，请使用已配置定位器执行步骤")
            raise RuntimeError(f"不支持的iOS远程控制事件：{event_type or '-'}")

    @classmethod
    async def _ios_coordinates(cls, driver, event: dict) -> tuple[float, float]:
        size = await asyncio.to_thread(driver.get_window_size)
        return cls._coordinates_from_viewport(event, {
            "width": max(1, int(size.get("width") or 1)),
            "height": max(1, int(size.get("height") or 1)),
        })

    @staticmethod
    def _ios_swipe_direction(event: dict) -> str:
        delta_x = float(event.get("delta_x", 0) or 0)
        delta_y = float(event.get("delta_y", 0) or 0)
        if abs(delta_x) > abs(delta_y):
            return "left" if delta_x > 0 else "right"
        return "up" if delta_y > 0 else "down"

    async def _list_pages(self) -> dict:
        pages = self._open_pages()
        log.debug(f"UI直播页签列表：{len(pages)} 个")
        return {
            "pages": [
                await self._page_payload(page, index)
                for index, page in enumerate(pages)
            ]
        }

    async def _switch_page(self, event: dict) -> dict:
        page = self._find_page(event)
        self.runtime_state.selected_scan_region = None
        self.runtime_state.selected_scan_region_page = None
        await UiRuntimeRegistry.set_active_page(self.runtime_state, page)
        try:
            await page.bring_to_front()
        except Exception:
            pass
        return await self._list_pages()

    async def _close_page(self, event: dict) -> dict:
        pages = self._open_pages()
        if len(pages) <= 1:
            raise RuntimeError("至少需要保留一个浏览器页面")
        page = self._find_page(event, pages)
        if self.runtime_state.selected_scan_region_page is page:
            self.runtime_state.selected_scan_region = None
            self.runtime_state.selected_scan_region_page = None
        active_page = self.runtime_state.page
        await page.close()
        remaining = self._open_pages()
        if active_page is page or active_page is None or active_page.is_closed():
            next_page = remaining[-1] if remaining else None
            await UiRuntimeRegistry.set_active_page(self.runtime_state, next_page)
            if next_page:
                try:
                    await next_page.bring_to_front()
                except Exception:
                    pass
        return await self._list_pages()

    def _context(self):
        context = getattr(self.runtime_state.base_data, "context", None)
        if context is None:
            raise RuntimeError("浏览器上下文不存在")
        return context

    def _open_pages(self) -> list:
        return [page for page in self._context().pages if not page.is_closed()]

    def _find_page(self, event: dict, pages: list | None = None):
        pages = pages or self._open_pages()
        page_id = str(event.get("page_id") or "")
        if page_id:
            for page in pages:
                if str(id(page)) == page_id:
                    return page
        if event.get("page_index") is not None:
            index = int(event.get("page_index"))
            if 0 <= index < len(pages):
                return pages[index]
        raise RuntimeError("没有找到指定浏览器页面")

    async def _page_payload(self, page, index: int) -> dict:
        try:
            title = await page.title()
        except Exception:
            title = ""
        return {
            "page_id": str(id(page)),
            "index": index,
            "title": title,
            "url": page.url,
            "active": page is self.runtime_state.page,
        }

    async def release_all(self) -> None:
        if getattr(self.runtime_state, "ios", None) is not None:
            self.pressed_buttons.clear()
            self.pressed_keys.clear()
            return
        page = self.runtime_state.page
        if page is None or page.is_closed():
            self.pressed_buttons.clear()
            self.pressed_keys.clear()
            return
        async with self.runtime_state.operation_lock:
            for button in tuple(self.pressed_buttons):
                try:
                    await page.mouse.up(button=button)
                except Exception:
                    pass
            for key in tuple(self.pressed_keys):
                try:
                    await page.keyboard.up(key)
                except Exception:
                    pass
            self.pressed_buttons.clear()
            self.pressed_keys.clear()

    async def _event_coordinates(self, page, event: dict) -> tuple[float, float]:
        return self._coordinates_from_viewport(event, await self._viewport_size(page))

    @staticmethod
    def _coordinates_from_viewport(event: dict, viewport: dict) -> tuple[float, float]:
        x = max(0.0, min(1.0, float(event.get("x", 0)))) * viewport["width"]
        y = max(0.0, min(1.0, float(event.get("y", 0)))) * viewport["height"]
        return x, y

    @staticmethod
    async def _viewport_size(page) -> dict:
        if page.viewport_size:
            return page.viewport_size
        try:
            size = await page.evaluate("""() => ({
                width: window.innerWidth || document.documentElement.clientWidth || 1280,
                height: window.innerHeight || document.documentElement.clientHeight || 720,
            })""")
            return {
                "width": max(1, int(size.get("width") or 1280)),
                "height": max(1, int(size.get("height") or 720)),
            }
        except Exception:
            return {"width": 1280, "height": 720}

    def _button(self, event: dict) -> str:
        button = event.get("button", "left")
        if button not in self.ALLOWED_BUTTONS:
            raise RuntimeError("不支持的鼠标按键")
        return button

    @staticmethod
    def _key(event: dict) -> str:
        key = str(event.get("key", ""))[:100]
        if not key:
            raise RuntimeError("键盘按键不能为空")
        return key

    async def _pick_element(self, page, x: float, y: float) -> dict:
        started_at = time.perf_counter()
        payload = await self.inspector.pick(page, x, y)
        self.runtime_state.selected_scan_region = payload
        self.runtime_state.selected_scan_region_page = page
        element_result = await self._pick_element_result(page, payload, started_at)
        log.debug(
            f"UI直播采集元素：tag={payload.get('tag')}, "
            f"text={(payload.get('text') or payload.get('label') or payload.get('placeholder') or '')[:40]}, "
            f"locators={len(payload.get('locators') or [])}"
        )
        return {"element": payload, "element_result": element_result}

    async def _pick_element_result(self, page, item: dict, started_at: float) -> dict:
        locators = item.get("locators") or []
        validation = item.get("validation") or {}
        selected = validation.get("selected") or {}
        locator = selected or (locators[0] if locators else {})
        match_count = selected.get("count", 1 if item.get("bounding_box") else 0)
        element_text = item.get("text") or item.get("label") or item.get("placeholder") or ""
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        picked_visible = bool(
            item.get("bounding_box", {}).get("width")
            and item.get("bounding_box", {}).get("height")
        )
        status = 1 if picked_visible else 0
        return {
            "id": 0,
            "name": element_text or item.get("tag") or "采集元素",
            "sleep": None,
            "type": 0,
            "ope_key": "采集元素",
            "ope_value": [],
            "duration_ms": duration_ms,
            "page_url": page.url,
            "page_title": await page.title(),
            "viewport": await self._viewport_size(page),
            "status": status,
            "error_message": None if status else "当前位置没有可采集元素",
            "locator_engine": {
                "used_source": "live_pick",
                "used_ai": False,
                "temporary_heal_used": False,
                "candidate_count": len(locators),
                "final_score": 100 if selected else 80 if picked_visible else 0,
                "reject_reasons": [] if selected else [
                    "已采集到鼠标位置元素，但推荐定位器未验证通过"
                ],
            },
            "elements": [{
                "loc": locator.get("loc") or item.get("xpath"),
                "exp": locator.get("exp") if locator.get("exp") is not None else 0,
                "ele_quantity": match_count,
                "element_text": element_text,
                "text_snippets": [element_text] if element_text else [],
                "visible": picked_visible,
                "enabled": selected.get("enabled"),
                "editable": selected.get("editable"),
                "bounding_box": item.get("bounding_box"),
                "locate_duration_ms": duration_ms,
                "sub": locator.get("sub"),
                "is_iframe": 0,
            }],
        }

    async def _check_locator(self, page, event: dict) -> dict:
        row_key = event.get("row_key")
        name = str(event.get("name") or "扫描元素检测")
        locators = [
            locator for locator in (event.get("locators") or [])
            if isinstance(locator, dict)
            and locator.get("loc")
            and locator.get("exp") is not None
        ][:5]
        inspection = await self.inspector.validate(
            page,
            locators,
            highlight=True,
            baseline_item={"text": "", "label": name, "placeholder": ""},
        )
        selected = inspection.get("selected") or {}
        selected_locator = {
            "exp": selected.get("exp"),
            "loc": selected.get("loc"),
            "sub": selected.get("sub"),
        } if selected else (locators[0] if locators else {})
        status = 1 if inspection.get("status") else 0
        selected_text = selected.get("element_text") or ""
        duration_ms = inspection.get("duration_ms") or 0
        result = {
            "id": 0,
            "name": name,
            "sleep": None,
            "type": 0,
            "ope_key": "扫描元素检测",
            "ope_value": [],
            "duration_ms": duration_ms,
            "page_url": page.url,
            "page_title": await page.title(),
            "viewport": await self._viewport_size(page),
            "status": status,
            "error_message": None if status else "扫描元素定位检测失败，请检查定位器是否准确",
            "locator_engine": {
                "used_source": "live_scan_check",
                "used_ai": False,
                "temporary_heal_used": False,
                "candidate_count": len(locators),
                "final_score": 100 if status else 0,
                "reject_reasons": inspection.get("reject_reasons") or [],
            },
            "locator_groups": inspection.get("locator_groups") or [],
            "selected_group": inspection.get("selected_group"),
            "elements": [{
                "loc": selected_locator.get("loc"),
                "exp": selected_locator.get("exp"),
                "ele_quantity": selected.get("count", 0),
                "element_text": selected_text,
                "text_snippets": [selected_text] if selected_text else [],
                "visible": bool(selected.get("visible")),
                "enabled": selected.get("enabled"),
                "editable": selected.get("editable"),
                "bounding_box": selected.get("bounding_box"),
                "locate_duration_ms": duration_ms,
                "sub": selected_locator.get("sub"),
                "is_iframe": 0,
            }],
        }
        return {
            "row_key": row_key,
            "scan_check_result": result,
            "baseline_snapshot": inspection.get("baseline_snapshot") or {},
        }
