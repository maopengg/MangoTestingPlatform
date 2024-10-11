# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-07-18 18:15
# @Author : 毛鹏
import traceback
from datetime import datetime

from src.enums.tools_enum import ClientTypeEnum
from src.network.web_socket.websocket_client import WebSocketClient
from src.settings import settings
from src.tools.desktop.signal_send import SignalSend
from src.tools.log_collector import log


def error_send(func, args, kwargs, error, trace):
    SignalSend.notice_signal_c(f'发生未知异常，请先自行查看错误信息后联系管理员！错误信息：{error}')
    log.error(
        f'错误函数：{func.__name__}，发送未知异常，请联系管理员！异常类型：{type(error)}，错误详情：{str(error)}， 错误详情：{trace}')
    content = f"""
      芒果测试平台管理员请注意查收:
          触发用户：{settings.USERNAME}
          触发时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
          错误函数：{func.__name__}
          异常类型: {type(error)}
          错误提示: {str(error)}
          错误详情：{trace}
          参数list：{args}
          参数dict：{kwargs}

      **********************************
      详细情况可前往芒果自动化平台查看，非相关负责人员可忽略此消息。谢谢！

                                                    -----------芒果自动化平台
      """
    from mangokit import Mango
    Mango.s(content)


def async_error_handle(is_error=False):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as error:
                trace = traceback.format_exc()
                error_send(func, args, kwargs, error, trace)
                await WebSocketClient().async_send(
                    code=300,
                    msg=f"发生未知异常，请先自行查看错误信息后联系管理员！错误信息：{error}",
                    is_notice=ClientTypeEnum.WEB.value
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
                error_send(func, args, kwargs, error, trace)
                WebSocketClient().sync_send(
                    code=300,
                    msg=f"发生未知异常，请先自行查看错误信息后联系管理员！错误信息：{error}",
                    is_notice=ClientTypeEnum.WEB.value
                )
                if is_error:
                    raise error

        wrapper.__name__ = func.__name__
        return wrapper

    return decorator
