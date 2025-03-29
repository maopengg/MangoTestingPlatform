# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-20 20:30
# @Author : 毛鹏
import asyncio
import traceback

from .consumer import SocketConsumer
from .network.web_socket.websocket_client import WebSocketClient
from .services.ui.service.case_flow import CaseFlow
from .tools.log_collector import log


async def process(parent):
    websocket_task = None
    consumer_task = None
    case_flow_task = None
    try:
        WebSocketClient.parent = parent
        SocketConsumer.parent = parent
        CaseFlow.parent = parent
        websocket_task = asyncio.create_task(WebSocketClient.client_run())
        consumer_task = asyncio.create_task(SocketConsumer.process_tasks())
        case_flow_task = asyncio.create_task(CaseFlow.process_tasks())
    except Exception as error:
        if websocket_task:
            websocket_task.cancel()
        if consumer_task:
            consumer_task.cancel()
        if case_flow_task:
            case_flow_task.cancel()
        if WebSocketClient.websocket:
            WebSocketClient.websocket = None
        traceback.print_exc()
        log.error(f"启动永久循环协程任务时出现异常：{error}")
        await asyncio.sleep(5)
        await process(parent)


async def test_process(parent):
    consumer_task = None
    case_flow_task = None
    try:
        SocketConsumer.parent = parent
        CaseFlow.parent = parent
        consumer_task = asyncio.create_task(SocketConsumer.process_tasks())
        case_flow_task = asyncio.create_task(CaseFlow.process_tasks())
    except Exception as error:
        if consumer_task:
            consumer_task.cancel()
        if case_flow_task:
            case_flow_task.cancel()
        if WebSocketClient.websocket:
            WebSocketClient.websocket = None
        traceback.print_exc()
        log.error(f"启动永久循环协程任务时出现异常：{error}")
        await asyncio.sleep(5)
        await test_process(parent)
