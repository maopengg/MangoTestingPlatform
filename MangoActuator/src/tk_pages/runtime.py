from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from concurrent.futures import Future
from queue import Empty, Queue
import threading
from typing import Any


UiCallback = tuple[Callable[..., Any], tuple[Any, ...]]


class AsyncRuntimeBridge:
    """Own an asyncio loop in a worker thread and marshal callbacks to Tk."""

    def __init__(self) -> None:
        self.loop: asyncio.AbstractEventLoop | None = None
        self.callbacks: Queue[UiCallback] = Queue()
        self._ready = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_loop, name="mango-asyncio", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=10):
            raise RuntimeError("后台异步事件循环启动超时")

    def _run_loop(self) -> None:
        from src.services.system_error_reporter import ActuatorSystemErrorReporter

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        ActuatorSystemErrorReporter.install_loop_exception_handler(loop)
        self.loop = loop
        self._ready.set()
        loop.run_forever()
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()

    def submit(
        self,
        coroutine: Coroutine[Any, Any, Any],
        on_success: Callable[[Any], Any] | None = None,
        on_error: Callable[[BaseException], Any] | None = None,
    ) -> Future:
        if self.loop is None:
            raise RuntimeError("后台异步事件循环尚未启动")
        future = asyncio.run_coroutine_threadsafe(coroutine, self.loop)

        if on_success or on_error:
            def finished(done: Future) -> None:
                try:
                    result = done.result()
                except BaseException as error:
                    if on_error:
                        self.callbacks.put((on_error, (error,)))
                else:
                    if on_success:
                        self.callbacks.put((on_success, (result,)))

            future.add_done_callback(finished)
        return future

    def drain_callbacks(self) -> list[UiCallback]:
        callbacks: list[UiCallback] = []
        while True:
            try:
                callbacks.append(self.callbacks.get_nowait())
            except Empty:
                return callbacks

    def stop(self, timeout: float = 10) -> None:
        if not self.loop or not self.loop.is_running():
            return

        async def shutdown() -> None:
            from src.network.web_socket.websocket_client import WebSocketClient
            from src.services.runtime import RuntimeSupervisor

            await RuntimeSupervisor.stop()
            await WebSocketClient.close()

        try:
            self.submit(shutdown()).result(timeout=timeout)
        except Exception:
            pass
        self.loop.call_soon_threadsafe(self.loop.stop)
        if self._thread:
            self._thread.join(timeout=timeout)
