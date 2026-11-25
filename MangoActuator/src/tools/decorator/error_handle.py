# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-07-18 18:15
# @Author : 毛鹏
import traceback

from mangotools.enums import ClientTypeEnum
from src.tools.log_collector import log
from src.services.system_error_reporter import ActuatorSystemErrorReporter


def async_error_handle(is_error=False):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as error:
                await ActuatorSystemErrorReporter.report(error, f'decorator:{func.__qualname__}')
                trace = traceback.format_exc()
                log.error(trace)
                from src.tools.executor_task_context import is_executor_task
                if is_executor_task():
                    # 数据库任务由统一工作器负责记录失败终态和可靠回传；这里继续
                    # 吞错会让工作器把实际失败误判为成功。
                    raise
                from src.network import socket_conn
                await socket_conn.async_send(
                    code=300,
                    msg=f"发生未知异常，请先自行查看错误信息后联系管理员！错误信息：{error}",
                    is_notice=ClientTypeEnum.WEB
                )
                if is_error:
                    raise error

        wrapper.__name__ = func.__name__
        return wrapper

    return decorator


def sync_error_handle(is_error=False):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as error:
                ActuatorSystemErrorReporter.schedule(error, f'decorator:{func.__qualname__}')
                trace = traceback.format_exc()
                log.error(trace)
                from src.tools.executor_task_context import is_executor_task
                if is_executor_task():
                    raise
                from src.network import socket_conn
                socket_conn.sync_send(
                    code=300,
                    msg=f"发生未知异常，请先自行查看错误信息后联系管理员！错误信息：{error}",
                    is_notice=ClientTypeEnum.WEB
                )
                if is_error:
                    raise error

        wrapper.__name__ = func.__name__
        return wrapper

    return decorator
