# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-09-08 14:00
# @Author : 毛鹏
import asyncio
from queue import Queue

from src.enums.gui_enum import TipsTypeEnum
from src.enums.tools_enum import MessageEnum
from src.models.tools_model import MessageModel
from src.tools.executor_task_context import format_executor_task_log
from src.tools.log_collector import log

global_msg_queue = Queue()


def _write_realtime_log(msg, level=None):
    text = format_executor_task_log(str(msg))
    if isinstance(level, TipsTypeEnum):
        level = level.name
    elif isinstance(level, int):
        try:
            level = TipsTypeEnum(level).name
        except ValueError:
            level = None
    normalized = str(level or '').lower()
    if normalized in {'debug'}:
        log.debug(text)
    elif normalized in {'error', 'fail', 'warning', 'warn'} or any(
            word in text for word in ('失败', '异常', '错误', '未找到', '超时', '队列已满')
    ):
        # 消息级 ERROR 是业务失败提示，不代表执行器自身发生系统错误。
        log.warning(text)
    elif normalized in {'info'}:
        log.info(text)
    else:
        log.debug(text)


def send_global_msg(msg, _type=MessageEnum.REAL_TIME, level=None, log_level=None):
    if _type == MessageEnum.REAL_TIME:
        _write_realtime_log(msg, log_level if log_level is not None else level)
    global_msg_queue.put(MessageModel(type=_type, msg=msg, level=level))


async def global_consumer_news():
    while True:
        if not global_msg_queue.empty():
            global_msg_queue.get()
        else:
            await asyncio.sleep(3)
