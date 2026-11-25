import asyncio
import traceback
import functools
import hashlib
import inspect
import threading
import time
import sys
import json
import re
from contextvars import ContextVar

from mangoautomation.reporting import developer_error, error_payload

from src.exceptions import MangoActuatorError
from src.tools.log_collector import log
from src.storage.sqlite.system_error_outbox import SystemErrorOutbox


class ActuatorSystemErrorReporter:
    """将执行器非预期异常上报到平台；上报失败不能影响原运行流程。"""

    MESSAGE_MAX_LENGTH = 500
    TRACEBACK_MAX_LENGTH = 50000
    _reporting = ContextVar('actuator_system_error_reporting', default=False)
    _recent = {}
    _recent_lock = threading.Lock()
    _pending_tasks = set()
    _hooks_installed = False
    _sending = set()

    @classmethod
    def should_report(cls, error):
        if isinstance(error, MangoActuatorError):
            return False
        # 平台明确拒绝/鉴权/HTTP 故障由服务端处理；格式错误（无状态码）需开发者排查。
        if type(error).__module__ == 'src.network.http.apis.base':
            return getattr(error, 'status_code', None) is None and str(error) == '执行器任务接口返回格式错误'
        return developer_error(error)

    @classmethod
    async def report(
            cls,
            error: BaseException,
            operation: str,
            *,
            traceback_text: str | None = None,
    ) -> bool:
        if not cls.should_report(error) or cls._reporting.get() or getattr(error, '_mango_system_error_reported', False):
            return False
        token = cls._reporting.set(True)
        fingerprint = None
        try:
            payload = error_payload(error, operation)
            from src.tools.executor_task_context import get_executor_task_log_context
            context = get_executor_task_log_context()
            identifiers = {key: str(context[key]) for key in
                           ('task_id', 'case_id', 'test_suite_id', 'test_suite_details', 'execution_id', 'slot_id', 'attempt', 'connection_id')
                           if key in context and re.fullmatch(r'[A-Za-z0-9:_-]{1,128}', str(context[key]))}
            if identifiers:
                payload['traceback'] = ('执行上下文：' + json.dumps(identifiers, ensure_ascii=False) + '\n' + payload['traceback'])[:cls.TRACEBACK_MAX_LENGTH]
            scope = cls._scope()
            fingerprint = hashlib.sha256((scope + repr(payload)).encode()).hexdigest()
            with cls._recent_lock:
                now = time.monotonic()
                cls._recent = {key: value for key, value in cls._recent.items() if now - value < 60}
                if len(cls._recent) >= 2048:
                    cls._recent.pop(next(iter(cls._recent)))
                if fingerprint in cls._recent:
                    error._mango_system_error_reported = True
                    return False
                cls._recent[fingerprint] = now
            SystemErrorOutbox.put(fingerprint, scope, payload)
            error._mango_system_error_reported = True
            await cls._send_payload(fingerprint, payload)
            return True
        except Exception as report_error:
            with cls._recent_lock:
                cls._recent.pop(fingerprint, None)
            log.debug(f'执行器系统异常上报失败，将保留本地日志；类型：{type(report_error).__name__}')
            return False
        finally:
            cls._reporting.reset(token)

    @staticmethod
    def _scope():
        from src.tools.set_config import SetConfig
        identity = str(SetConfig.get_host() or '').rstrip('/') + '\0' + str(SetConfig.get_username() or '')
        return hashlib.sha256(identity.encode()).hexdigest()

    @classmethod
    async def _send_payload(cls, fingerprint, payload, retries=0):
        with cls._recent_lock:
            if fingerprint in cls._sending:
                return
            cls._sending.add(fingerprint)
        try:
            from src.network import HTTP
            await HTTP.actuator_tasks.report_system_error(
                operation=payload['operation'], exception_type=payload['exception_type'],
                message=payload['message'], traceback_text=payload['traceback'])
            SystemErrorOutbox.acknowledge(fingerprint)
        except Exception as error:
            SystemErrorOutbox.failed(fingerprint, retries)
            log.debug(f'执行器异常记录暂未送达，已保留待补传；类型：{type(error).__name__}')
        finally:
            with cls._recent_lock:
                cls._sending.discard(fingerprint)

    @classmethod
    async def flush_pending(cls):
        token = cls._reporting.set(True)
        try:
            for row in SystemErrorOutbox.due(cls._scope()):
                await cls._send_payload(row['fingerprint'], row['payload'], row['retries'])
        finally:
            cls._reporting.reset(token)

    @classmethod
    async def run(cls):
        while True:
            try:
                await cls.flush_pending()
            except Exception as error:
                # 发件箱自身不可用时只留固定类型日志，避免递归写入同一个坏发件箱。
                log.warning(f'执行器异常补传暂不可用；类型：{type(error).__name__}')
            await asyncio.sleep(10)

    @classmethod
    def schedule(cls, error, operation):
        """同步回调/GUI 捕获点不阻塞事件循环；保存 Task 引用直至发送完成。"""
        if not cls.should_report(error):
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # 同步线程不存在 event loop 时，单独运行短时上报，不能静默漏掉异常。
            asyncio.run(cls.report(error, operation))
            return
        task = loop.create_task(cls.report(error, operation), name='report-actuator-system-error')
        cls._pending_tasks.add(task)
        task.add_done_callback(cls._pending_tasks.discard)

    @classmethod
    def install_loop_exception_handler(cls, loop: asyncio.AbstractEventLoop) -> None:
        if getattr(loop, '_mango_error_handler_installed', False):
            return
        loop._mango_error_handler_installed = True
        previous_handler = loop.get_exception_handler()

        def handle_exception(current_loop, context):
            error = context.get('exception')
            if not isinstance(error, BaseException):
                error = RuntimeError(str(context.get('message') or '异步事件循环发生未知异常'))
            operation = f"asyncio:{cls._task_name(context.get('task') or context.get('future'))}"
            current_loop.create_task(
                cls.report(error, operation, traceback_text=cls._format_exception(error)),
                name='report-actuator-system-error',
            )
            if previous_handler:
                previous_handler(current_loop, context)
            else:
                current_loop.default_exception_handler(context)

        loop.set_exception_handler(handle_exception)

    @classmethod
    def install_exception_hooks(cls):
        if cls._hooks_installed:
            return
        cls._hooks_installed = True
        previous = sys.excepthook
        previous_thread = threading.excepthook
        def handle(exc_type, error, tb):
            cls.schedule(error, 'process:unhandled')
            previous(exc_type, error, tb)
        def handle_thread(args):
            cls.schedule(args.exc_value, 'thread:unhandled')
            previous_thread(args)
        sys.excepthook = handle
        threading.excepthook = handle_thread

    @staticmethod
    def _task_name(task) -> str:
        if task is None:
            return 'unhandled-task'
        get_name = getattr(task, 'get_name', None)
        return str(get_name() if callable(get_name) else type(task).__name__)[:200]

    @staticmethod
    def _format_exception(error: BaseException) -> str:
        return ''.join(traceback.format_exception(type(error), error, error.__traceback__))


def report_unexpected(func):
    """仅补报异常，不吞错，不改变任务成功/失败与取消语义。"""
    if inspect.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as error:
                await ActuatorSystemErrorReporter.report(error, func.__qualname__)
                raise
        return async_wrapper
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as error:
            ActuatorSystemErrorReporter.schedule(error, func.__qualname__)
            raise
    return sync_wrapper
