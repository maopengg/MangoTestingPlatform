import asyncio
import traceback
from contextvars import ContextVar

from src.exceptions import MangoActuatorError
from src.tools.log_collector import log


class ActuatorSystemErrorReporter:
    """将执行器非预期异常上报到平台；上报失败不能影响原运行流程。"""

    MESSAGE_MAX_LENGTH = 500
    TRACEBACK_MAX_LENGTH = 50000
    _reporting = ContextVar('actuator_system_error_reporting', default=False)

    @classmethod
    async def report(
            cls,
            error: BaseException,
            operation: str,
            *,
            traceback_text: str | None = None,
    ) -> bool:
        if isinstance(error, (asyncio.CancelledError, MangoActuatorError)) or cls._reporting.get():
            return False
        token = cls._reporting.set(True)
        try:
            from src.network import HTTP

            await HTTP.actuator_tasks.report_system_error(
                operation=str(operation or 'unknown')[:255],
                exception_type=type(error).__name__[:128],
                message=(str(error) or type(error).__name__)[:cls.MESSAGE_MAX_LENGTH],
                traceback_text=(traceback_text or traceback.format_exc())[:cls.TRACEBACK_MAX_LENGTH],
            )
            return True
        except Exception as report_error:
            log.debug(f'执行器系统异常上报失败，将保留本地日志：{report_error}')
            return False
        finally:
            cls._reporting.reset(token)

    @classmethod
    def install_loop_exception_handler(cls, loop: asyncio.AbstractEventLoop) -> None:
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

    @staticmethod
    def _task_name(task) -> str:
        if task is None:
            return 'unhandled-task'
        get_name = getattr(task, 'get_name', None)
        return str(get_name() if callable(get_name) else type(task).__name__)[:200]

    @staticmethod
    def _format_exception(error: BaseException) -> str:
        return ''.join(traceback.format_exception(type(error), error, error.__traceback__))
