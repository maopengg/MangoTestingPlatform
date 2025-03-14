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
    """
    启动三个永久循环的协程任务
    @param parent: 父对象，通常是WindowLogic实例
    @return:
    """
    try:
        # 设置父对象
        WebSocketClient.parent = parent
        SocketConsumer.parent = parent
        CaseFlow.parent = parent
        
        log.info("开始启动三个永久循环的协程任务...")
        
        # 创建三个任务
        websocket_task = asyncio.create_task(WebSocketClient.client_run())
        consumer_task = asyncio.create_task(SocketConsumer.process_tasks())
        case_flow_task = asyncio.create_task(CaseFlow.process_tasks())
        
        log.info("三个永久循环的协程任务已启动")
        
        # 等待所有任务完成（实际上不会完成，因为它们是永久循环）
        await asyncio.gather(
            websocket_task,
            consumer_task,
            case_flow_task
        )
    except Exception as error:
        traceback.print_exc()
        log.error(f"启动永久循环协程任务时出现异常：{error}")
        await asyncio.sleep(5)
        await process(parent)