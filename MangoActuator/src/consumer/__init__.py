# -*- coding: utf-8 -*-
# @Project: 芒果测试平台# @Description:
# @Time   : 2023/5/10 11:34
# @Author : 毛鹏
import asyncio
import json
import traceback

from src.consumer.api import API
from src.consumer.perf import Perf
from src.consumer.tools import Tools
from src.consumer.ui import UI
from src.models.socket_model import QueueModel
from src.models.user_model import UserModel
from src.settings import settings
from src.tools.log_collector import log


class SocketConsumer(UI, API, Perf, Tools):
    queue = asyncio.Queue()
    parent = None
    running = True

    @classmethod
    async def add_task(cls, task):
        await cls.queue.put(task)

    @classmethod
    async def set_log(cls, debug: bool = False):
        settings.IS_DEBUG = debug
        log.set_debug(settings.IS_DEBUG)

    @classmethod
    async def process_tasks(cls):
        while cls.running:
            if not cls.queue.empty():
                data: QueueModel = await cls.queue.get()
                await getattr(cls, data.func_name)(data.func_args)
                # task = cls.parent.loop.create_task(getattr(cls, data.func_name)(data.func_args))
                # task.add_done_callback(cls.handle_task_result)
            else:
                await asyncio.sleep(0.1)

    @classmethod
    def handle_task_result(cls, task):
        try:
            result = task.result()
        except Exception as error:
            traceback.print_exc()
            log.error(f"反射任务执行出现异常：{error}")

    @classmethod
    def stop(cls):
        cls.running = False
