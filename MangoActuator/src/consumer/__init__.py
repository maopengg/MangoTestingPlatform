# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023/5/10 11:34
# @Author : 毛鹏
import asyncio
import traceback

from src.consumer.api import API
from src.consumer.perf import Perf
from src.consumer.tools import Tools
from src.consumer.ui import UI
from src.consumer.pytest import Pytest
from mangotools.contracts import SocketCommandContract
from src.settings import settings
from src.tools.log_collector import log
from src.services.system_error_reporter import ActuatorSystemErrorReporter


class SocketConsumer(UI, API, Perf, Tools, Pytest):
    queue = asyncio.Queue()
    parent = None
    running = True
    immediate_functions = {
        'u_live_stream_start',
        'u_live_stream_stop',
        'u_live_workspace_start',
        'u_live_workspace_stop',
        't_stop_test_suite',
        'perf_execution',
    }
    background_tasks: set[asyncio.Task] = set()

    @classmethod
    async def add_task(cls, task):
        if task.func_name in cls.immediate_functions:
            background_task = asyncio.create_task(
                cls._execute_task(task),
                name=f'websocket-immediate:{task.func_name}',
            )
            cls.background_tasks.add(background_task)
            background_task.add_done_callback(cls.background_tasks.discard)
            return
        await cls.queue.put(task)

    @classmethod
    async def set_log(cls, debug: bool = False):
        settings.IS_DEBUG = debug
        log.set_debug(settings.IS_DEBUG)

    @classmethod
    async def process_tasks(cls):
        while cls.running:
            try:
                if not cls.queue.empty():
                    data: SocketCommandContract = await cls.queue.get()
                    await cls._execute_task(data)
                    # task = cls.parent.loop.create_task(getattr(cls, data.func_name)(data.func_args))
                    # task.add_done_callback(cls.handle_task_result)
                else:
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                trace = traceback.format_exc()
                await ActuatorSystemErrorReporter.report(
                    error,
                    'websocket-command-consumer',
                    traceback_text=trace,
                )
                traceback.print_exc()
                log.error(
                    f"WebSocket反射任务执行异常，consumer继续运行，"
                    f"类型：{type(error)}，详情：{error}，明细：{trace}"
                )
                await asyncio.sleep(0.1)

    @classmethod
    async def _execute_task(cls, data: SocketCommandContract):
        func = getattr(cls, data.func_name, None)
        if not func:
            error = f"反射函数不存在：{data.func_name}"
            log.error(f"WebSocket{error}")
            await cls._acknowledge(data.dispatch_id, False, error)
            return
        try:
            result = await func(data.func_args)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            error_message = str(error) or f"{type(error).__name__}"
            await cls._acknowledge(data.dispatch_id, False, error_message)
            if data.func_name in {'u_live_stream_start', 'u_live_workspace_start'} and (
                    '等待UI实时画面运行页面超时' in error_message
                    or '直播会话尚无观看者' in error_message
            ):
                log.warning(
                    f"WebSocket实时画面任务执行失败：func={data.func_name}, "
                    f"详情：{error_message}。这通常是旧工作区或订阅端已重连导致，可由前端重新创建工作区恢复。"
                )
                return
            trace = traceback.format_exc()
            await ActuatorSystemErrorReporter.report(
                error,
                f'websocket-command:{data.func_name}',
                traceback_text=trace,
            )
            log.error(
                f"WebSocket反射任务执行异常：func={data.func_name}, "
                f"类型：{type(error)}，详情：{error_message}，明细：{trace}"
            )
        else:
            await cls._acknowledge(data.dispatch_id, True)
            return result

    @classmethod
    async def execute_executor_task(cls, func_name: str, func_args):
        """执行数据库任务载荷；异常交给统一任务工作器形成终态。"""
        func = getattr(cls, func_name, None)
        if not func:
            raise RuntimeError(f'执行器不支持任务方法：{func_name}')
        return await func(func_args)

    @staticmethod
    async def _acknowledge(dispatch_id: str | None, success: bool, error: str | None = None):
        if not dispatch_id:
            return
        from src.network.web_socket.websocket_client import WebSocketClient

        await WebSocketClient._send_direct(
            '命令处理完成' if success else '命令处理失败',
            func_name='command_ack',
            func_args={
                'dispatch_id': dispatch_id,
                'success': success,
                'error': error,
            },
        )

    @classmethod
    def handle_task_result(cls, task):
        try:
            result = task.result()
        except Exception as error:
            traceback.print_exc()
            log.error(f"反射任务执行出现异常：{error}")

    @classmethod
    def stop(cls):
        cls.running = False
        for task in tuple(cls.background_tasks):
            task.cancel()
