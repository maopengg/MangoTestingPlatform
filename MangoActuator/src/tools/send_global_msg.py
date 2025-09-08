# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-09-08 14:00
# @Author : 毛鹏
import asyncio
from queue import Queue

from src.enums.tools_enum import MessageEnum
from src.models.tools_model import MessageModel

global_msg_queue = Queue()


def send_global_msg(msg, _type=MessageEnum.REAL_TIME, level=None):
    global_msg_queue.put(MessageModel(type=_type, msg=msg, level=level))


async def global_consumer_news():
    while True:
        if not global_msg_queue.empty():
            msg: MessageModel = global_msg_queue.get()
            print(msg.model_dump_json())
        else:
            await asyncio.sleep(3)
