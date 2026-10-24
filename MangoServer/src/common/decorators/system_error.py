import inspect
import traceback
from functools import wraps

from asgiref.sync import sync_to_async
from django.conf import settings
from django.utils.module_loading import import_string


def report_system_error(
        error: Exception,
        *,
        source: str,
        request_path: str | None = None,
        service_name: str | None = None,
        request=None,
        trace: str | None = None,
) -> None:
    """统一上报非预期系统异常，且不影响原异常处理流程。"""
    reporter = import_string(settings.SYSTEM_ERROR_REPORTER)
    reporter(
        error,
        source,
        request=request,
        request_path=request_path,
        service_name=service_name,
        trace=trace or traceback.format_exc(),
    )


async def areport_system_error(
        error: Exception,
        *,
        source: str,
        request_path: str | None = None,
        service_name: str | None = None,
        request=None,
) -> None:
    trace = traceback.format_exc()
    await sync_to_async(report_system_error, thread_sensitive=True)(
        error,
        source=source,
        request_path=request_path,
        service_name=service_name,
        request=request,
        trace=trace,
    )


def system_error_guard(
        *,
        source: str,
        request_path: str | None = None,
        service_name: str | None = None,
):
    """为同步或异步后台入口记录异常，记录后保持原样抛出。"""

    def decorator(func):
        path = request_path or func.__qualname__
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as error:
                    await areport_system_error(
                        error,
                        source=source,
                        request_path=path,
                        service_name=service_name,
                    )
                    raise

            return async_wrapper

        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as error:
                report_system_error(
                    error,
                    source=source,
                    request_path=path,
                    service_name=service_name,
                )
                raise

        return wrapper

    return decorator
