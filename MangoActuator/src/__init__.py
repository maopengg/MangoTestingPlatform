# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-20 20:30
# @Author : 毛鹏
import asyncio
import traceback

from src.services.ui.case_flow import CaseFlow
from src.tools.set_config import SetConfig
from .consumer import SocketConsumer
from .enums.tools_enum import CacheKeyEnum
from .network.web_socket import WebSocketClient, socket_conn
from .services.pytest.case_flow import PytestCaseFlow
from .tools import project_dir
from .tools.log_collector import log


async def process(parent, is_login=False, retry=0):
    websocket_task = None
    consumer_task = None
    case_flow_task = None
    try:
        WebSocketClient.parent = parent
        SocketConsumer.parent = parent
        CaseFlow.parent = parent
        PytestCaseFlow.parent = parent
        websocket_task = asyncio.create_task(WebSocketClient.client_run())
        consumer_task = asyncio.create_task(SocketConsumer.process_tasks())
        case_flow_task = asyncio.create_task(CaseFlow.process_tasks())
        case_flow_task = asyncio.create_task(PytestCaseFlow.process_tasks())
        if is_login:
            from src.network import HTTP
            from src.settings import settings
            from mangotools.data_processor import EncryptionTool
            HTTP.not_auth.login(SetConfig.get_username(), SetConfig.get_password())  # type:
        retry = 0
    except Exception as error:
        if websocket_task:
            websocket_task.cancel()
        if consumer_task:
            consumer_task.cancel()
        if case_flow_task:
            case_flow_task.cancel()
        if socket_conn.websocket:
            socket_conn.websocket = None
        traceback.print_exc()
        log.error(f"启动永久循环协程任务时出现异常：{error}")
        await asyncio.sleep(5)
        if retry >= 20:
            raise error
        else:
            await process(parent, is_login=is_login, retry=retry + 1)


async def test_process(parent):
    consumer_task = None
    case_flow_task = None
    try:
        SocketConsumer.parent = parent
        CaseFlow.parent = parent
        PytestCaseFlow.parent = parent
        consumer_task = asyncio.create_task(SocketConsumer.process_tasks())
        case_flow_task = asyncio.create_task(CaseFlow.process_tasks())
        case_flow_task = asyncio.create_task(PytestCaseFlow.process_tasks())
    except Exception as error:
        if consumer_task:
            consumer_task.cancel()
        if case_flow_task:
            case_flow_task.cancel()
        if socket_conn.websocket:
            socket_conn.websocket = None
        traceback.print_exc()
        log.error(f"启动永久循环协程任务时出现异常：{error}")
        await asyncio.sleep(5)
        await test_process(parent)
