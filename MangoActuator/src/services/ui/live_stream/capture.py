from src.services.system_error_reporter import ActuatorSystemErrorReporter
import asyncio
import base64
from contextlib import suppress

from src.tools.log_collector import log


class LatestFrameBuffer:
    def __init__(self):
        self.queue = asyncio.Queue(maxsize=1)

    def offer(self, frame: bytes) -> None:
        if self.queue.full():
            with suppress(asyncio.QueueEmpty):
                self.queue.get_nowait()
        self.queue.put_nowait(frame)

    async def get(self) -> bytes:
        return await self.queue.get()


class RuntimeFrameCapture:
    def __init__(self, runtime_state, config: dict, buffer: LatestFrameBuffer):
        self.runtime_state = runtime_state
        self.config = config
        self.buffer = buffer
        self.running = True

    async def run(self) -> None:
        if getattr(self.runtime_state, 'ios', None) is not None:
            await self._capture_ios()
            return
        while self.running:
            page = self.runtime_state.page
            if page is None or page.is_closed():
                await asyncio.sleep(0.2)
                continue
            try:
                await self._capture_cdp(page)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                await ActuatorSystemErrorReporter.report(error, 'services/ui/live_stream/capture:run')
                log.warning(f"CDP实时画面不可用，降级为截图采集：{error}")
                await self._capture_screenshots(page)

    def stop(self) -> None:
        self.running = False

    async def _capture_cdp(self, page) -> None:
        context = page.context
        browser = context.browser
        if browser is None or browser.browser_type.name != "chromium":
            raise RuntimeError("当前浏览器不支持CDP Screencast")
        session = await context.new_cdp_session(page)

        async def handle_frame(params):
            try:
                self.buffer.offer(base64.b64decode(params["data"]))
            finally:
                await session.send(
                    "Page.screencastFrameAck",
                    {"sessionId": params["sessionId"]},
                )

        session.on("Page.screencastFrame", handle_frame)
        await session.send(
            "Page.startScreencast",
            {
                "format": "jpeg",
                "quality": int(self.config.get("quality", 55)),
                "maxWidth": int(self.config.get("max_width", 1280)),
                "maxHeight": int(self.config.get("max_height", 720)),
                "everyNthFrame": 1,
            },
        )
        try:
            while self.running and self.runtime_state.page is page and not page.is_closed():
                await asyncio.sleep(0.2)
        finally:
            with suppress(Exception):
                await session.send("Page.stopScreencast")
            with suppress(Exception):
                await session.detach()

    async def _capture_screenshots(self, page) -> None:
        interval = 1 / max(1, min(int(self.config.get("fps", 3)), 5))
        while self.running and self.runtime_state.page is page and not page.is_closed():
            started = asyncio.get_running_loop().time()
            frame = await page.screenshot(
                type="jpeg",
                quality=int(self.config.get("quality", 55)),
                timeout=5000,
            )
            self.buffer.offer(frame)
            elapsed = asyncio.get_running_loop().time() - started
            await asyncio.sleep(max(0, interval - elapsed))

    async def _capture_ios(self) -> None:
        interval = 1 / max(1, min(int(self.config.get('fps', 3)), 5))
        while self.running and getattr(self.runtime_state, 'ios', None) is not None:
            started = asyncio.get_running_loop().time()
            frame = await asyncio.to_thread(self.runtime_state.ios.get_screenshot_as_png)
            self.buffer.offer(frame)
            elapsed = asyncio.get_running_loop().time() - started
            await asyncio.sleep(max(0, interval - elapsed))


PlaywrightFrameCapture = RuntimeFrameCapture
