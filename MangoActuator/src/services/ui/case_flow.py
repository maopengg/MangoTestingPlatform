# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-04-26 10:53
# @Author : 毛鹏

import asyncio
import time
import traceback

from mangokit.uidrive import DriverObject

from src.models.ui_model import CaseModel, GetTaskModel
from src.services.ui.test_case import TestCase
from src.tools.decorator.memory import async_memory
from src.tools.log_collector import log
from src.tools.set_config import SetConfig

class CaseFlow:
    queue = asyncio.Queue()
    max_tasks = 2
    running_tasks = 0
    parent = None
    driver_object = DriverObject(True)
    running = True

    @classmethod
    async def process_tasks(cls):
        s = time.time()

        while cls.running:
            await asyncio.sleep(0.1)
            if cls.running_tasks < SetConfig.get_web_parallel() and not cls.queue.empty():# type: ignore
                case_model: CaseModel = await cls.queue.get()
                cls.running_tasks += 1
                task = asyncio.create_task(cls.execute_task(case_model))
            else:
                if time.time() - s > 5:
                    s = time.time()
                    await cls.get_case_task()

    @classmethod
    async def get_case_task(cls):
        try:
            from src.network import UiSocketEnum, WebSocketClient
            from src import CacheKeyEnum
            from src.tools.set_config import SetConfig
            await WebSocketClient.async_send(
                '请求获取任务',
                func_name=UiSocketEnum.GET_TASK.value,
                func_args=GetTaskModel(username=SetConfig.get_username())  # type: ignore
            )
        except Exception as error:
            log.error(f'get_case_task失败，类型：{type(error)}，失败详情：{error}，失败明细：{traceback.format_exc()}')

    @classmethod
    @async_memory
    async def execute_task(cls, case_model: CaseModel):
        async with TestCase(cls.parent, case_model, cls.driver_object) as obj:
            cls.parent.set_tips_info(f'开始执行UI测试用例：{case_model.name}')
            await obj.case_init()
            await obj.case_page_step()
            cls.running_tasks -= 1

    @classmethod
    async def add_task(cls, case_model: CaseModel):
        await cls.queue.put(case_model)

    @classmethod
    def stop(cls):
        cls.running = False
