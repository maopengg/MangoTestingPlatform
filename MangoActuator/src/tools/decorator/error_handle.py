# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-07-18 18:15
# @Author : 毛鹏
import traceback

from mangotools.mangos import Mango

from src.enums.system_enum import ClientTypeEnum
from src.enums.tools_enum import CacheKeyEnum
from src.network.web_socket.websocket_client import WebSocketClient
from src.settings.settings import IS_SEND_MAIL
from src.tools.log_collector import log
from src.tools.set_config import SetConfig


def async_error_handle(is_error=False):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as error:
                trace = traceback.format_exc()
                log.error(trace)
                if IS_SEND_MAIL:
                    from src import project_dir
                    Mango.s(func, error, trace, SetConfig.get_username(), args, kwargs)  # type: ignore
                await WebSocketClient().async_send(
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
                trace = traceback.format_exc()
                if IS_SEND_MAIL:
                    from src import project_dir
                    Mango.s(func, error, trace,
                            SqlCache(project_dir.cache_file()).get_sql_cache(CacheKeyEnum.USERNAME.value), args, kwargs)
                WebSocketClient().sync_send(
                    code=300,
                    msg=f"发生未知异常，请先自行查看错误信息后联系管理员！错误信息：{error}",
                    is_notice=ClientTypeEnum.WEB
                )
                if is_error:
                    raise error

        wrapper.__name__ = func.__name__
        return wrapper

    return decorator
