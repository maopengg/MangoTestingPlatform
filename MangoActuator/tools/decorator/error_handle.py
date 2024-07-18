# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-07-18 18:15
# @Author : 毛鹏
import traceback

from enums.tools_enum import ClientTypeEnum
from service_conn.socket_conn.client_socket import ClientWebSocket
from tools.desktop.signal_send import SignalSend
from tools.log_collector import log
from tools.notic_tools import NoticeMain


def error_send(func, args, kwargs, error, trace):
    SignalSend.notice_signal_c(f'发送未知异常，请联系管理员！')
    log.error(f'错误函数：{func.__name__}，发送未知异常，请联系管理员！异常类型：{type(error)}，错误详情：{str(error)}， 错误详情：{trace}')
    content = f"""
      芒果测试平台管理员请注意查收:
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
    NoticeMain.mail_send(content)
    ClientWebSocket().sync_send(
        code=300,
        msg="发生未知异常！请联系管理员",
        is_notice=ClientTypeEnum.WEB.value
    )


def async_error_handle(is_error=False):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as error:
                trace = traceback.format_exc()
                error_send(func, args, kwargs, error, trace)
                if is_error:
                    raise error
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
                if is_error:
                    raise error

        return wrapper

    return decorator
