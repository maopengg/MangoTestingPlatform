import queue
import threading
import time
from concurrent.futures import Future
from contextvars import ContextVar
from dataclasses import dataclass

from greenlet import getcurrent, greenlet

_cooperative = ContextVar('cooperative_case_execution', default=False)


@dataclass
class WaitUntil:
    ready: object
    deadline: float
    interval: float


def wait_until(ready, timeout, interval=0.5, *, on_resume=None):
    """只在明确启用的 Case 线程让出执行权；不跨线程恢复 greenlet。"""
    deadline = time.monotonic() + timeout
    while not ready():
        if time.monotonic() >= deadline:
            return False
        if _cooperative.get():
            from django.db import connections
            if any(connection.in_atomic_block for connection in connections.all(initialized_only=True)):
                time.sleep(interval)
            else:
                getcurrent().parent.switch(WaitUntil(ready, deadline, interval))
                if on_resume is not None:
                    on_resume()
        else:
            time.sleep(interval)
    return True


def cooperative_sleep(seconds):
    if not _cooperative.get():
        time.sleep(seconds)
        return
    deadline = time.monotonic() + seconds
    wait_until(lambda: time.monotonic() >= deadline, seconds + 1, interval=min(0.1, max(seconds, 0.001)))


class CooperativeCaseExecutor:
    def __init__(self, max_workers, thread_name_prefix):
        self.queue = queue.Queue()
        self.stopping = threading.Event()
        self.threads = [threading.Thread(target=self.run, name=f'{thread_name_prefix}-{index}')
                        for index in range(max_workers)]
        for thread in self.threads:
            thread.start()

    def submit(self, callback, *args, **kwargs):
        future = Future()
        self.queue.put((future, callback, args, kwargs))
        return future

    def run(self):
        suspended = []
        while not self.stopping.is_set() or suspended or not self.queue.empty():
            now = time.monotonic()
            for entry in list(suspended):
                child, signal, future, due = entry
                if now < due:
                    continue
                try:
                    ready = signal.ready() or now >= signal.deadline
                except BaseException as error:
                    suspended.remove(entry)
                    self.resume(child, future, suspended, error=error)
                else:
                    if ready:
                        suspended.remove(entry)
                        self.resume(child, future, suspended)
                    else:
                        entry[3] = now + signal.interval
            if suspended:
                # greenlet 不能抢占同步驱动/用户函数，也不能跨线程恢复。
                # 同一线程不得再接手另一个 Case，否则其长同步操作会饿死已就绪的原 Case。
                # 其他空闲线程仍可领取任务；总执行容量仍由 max_workers 控制。
                delay = min(max(0, entry[3] - time.monotonic()) for entry in suspended)
                time.sleep(min(0.1, delay))
                continue
            try:
                future, callback, args, kwargs = self.queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if not future.set_running_or_notify_cancel():
                continue

            def invoke(callback=callback, args=args, kwargs=kwargs):
                token = _cooperative.set(True)
                try:
                    return callback(*args, **kwargs)
                finally:
                    _cooperative.reset(token)

            self.resume(greenlet(invoke), future, suspended)

    @staticmethod
    def resume(child, future, suspended, error=None):
        try:
            signal = child.throw(error) if error is not None else child.switch()
            if child.dead:
                future.set_result(signal)
            elif isinstance(signal, WaitUntil):
                suspended.append([child, signal, future, time.monotonic() + signal.interval])
            else:
                future.set_exception(RuntimeError('Invalid cooperative wait state'))
        except BaseException as error:
            future.set_exception(error)

    def shutdown(self, wait=True):
        self.stopping.set()
        if wait:
            for thread in self.threads:
                thread.join()
