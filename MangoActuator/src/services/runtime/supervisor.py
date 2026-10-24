# -*- coding: utf-8 -*-
import asyncio
import traceback
from collections.abc import Callable, Coroutine

from src.tools.log_collector import log
from src.services.system_error_reporter import ActuatorSystemErrorReporter


class RuntimeSupervisor:
    tasks: dict[str, asyncio.Task] = {}
    stopping = False
    restart_interval = 3

    @classmethod
    def start_task(cls, name: str, coro_factory: Callable[[], Coroutine]):
        task = cls.tasks.get(name)
        if task and not task.done():
            return task
        cls.stopping = False
        task = asyncio.create_task(cls._run_forever(name, coro_factory), name=name)
        cls.tasks[name] = task
        log.info(f'长期任务已启动：{name}')
        return task

    @classmethod
    async def _run_forever(cls, name: str, coro_factory: Callable[[], Coroutine]):
        while not cls.stopping:
            try:
                await coro_factory()
                if not cls.stopping:
                    log.warning(f'长期任务提前结束，将自动重启，task={name}')
                    await asyncio.sleep(cls.restart_interval)
            except asyncio.CancelledError:
                log.info(f'长期任务已取消：{name}')
                raise
            except Exception as error:
                trace = traceback.format_exc()
                await ActuatorSystemErrorReporter.report(
                    error,
                    f'runtime:{name}',
                    traceback_text=trace,
                )
                log.error(
                    f'长期任务异常退出，将自动重启，task={name}，'
                    f'类型：{type(error)}，详情：{error}，明细：{trace}'
                )
                await asyncio.sleep(cls.restart_interval)

    @classmethod
    async def stop(cls):
        cls.stopping = True
        tasks = list(cls.tasks.items())
        # 先通知任务工作线程停止领取并等待在途任务，再断开 WebSocket，
        # 保证 draining 状态能在连接仍在线时成功写入服务端。
        tasks.sort(key=lambda item: item[0] != 'executor_task_worker')
        for name, task in tasks:
            if task.done():
                continue
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as error:
                await ActuatorSystemErrorReporter.report(
                    error,
                    f'runtime-stop:{name}',
                    traceback_text=traceback.format_exc(),
                )
                log.error(f'停止长期任务异常，task={name}，详情：{error}，明细：{traceback.format_exc()}')
        cls.tasks.clear()
