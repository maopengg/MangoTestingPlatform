# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-04-29 16:27
# @Author : 毛鹏
import traceback

from enums.tools_enum import ClientTypeEnum
from service.socket_client.client_socket import ClientWebSocket
from tools.desktop.signal_send import SignalSend
from tools.log_collector import log


async def async_global_exception(fun_name: str, error, func_name=None, func_args=None, _is=True):
    if _is:
        traceback.print_exc()  # 打印异常追踪信息
        SignalSend.notice_signal_c(f'发送未知异常，请联系管理员！异常类型：{type(error)}')
        log.error(f'函数：{fun_name}，发送未知异常，请联系管理员！异常类型：{type(error)}，错误详情：{str(error)}')
        await ClientWebSocket().async_send(
            code=300,
            msg="发生未知异常！请联系管理员",
            is_notice=ClientTypeEnum.WEB.value,
            func_name=func_name,
            func_args=func_args,
        )
    else:
        raise error


def sync_global_exception(fun_name: str, error, _is=True):
    if _is:
        SignalSend.notice_signal_c(f'发送未知异常，请联系管理员！异常类型：{type(error)}')
        log.error(f'函数：{fun_name}，发送未知异常，请联系管理员！异常类型：{type(error)}，错误详情：{str(error)}')
        ClientWebSocket().sync_send(
            code=300,
            msg="发生未知异常！请联系管理员",
            is_notice=ClientTypeEnum.WEB.value
        )
    else:
        raise error
