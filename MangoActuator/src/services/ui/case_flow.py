# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-04-26 10:53
# @Author : 毛鹏

import asyncio
import time
import traceback

from mangoautomation.uidrive import DriverObject

from src.enums.tools_enum import TestCaseTypeEnum
from src.models.system_model import GetTaskModel
from src.models.ui_model import CaseModel
from src.services.ui.test_case import TestCase
from src.settings import settings
from src.tools.decorator.memory import async_memory
from src.tools.log_collector import log
from src.tools.send_global_msg import send_global_msg
from src.tools.set_config import SetConfig


class CaseFlow:
    queue = asyncio.Queue()
    running_tasks = 0
    parent = None
    driver_object = DriverObject(log, True)
    running = True

    @classmethod
    async def process_tasks(cls):
        last_get_time = 0

        while cls.running:
            await asyncio.sleep(0.1)

            max_parallel = SetConfig.get_web_parallel()
            allow_max = max_parallel + 1

            if cls.running_tasks < max_parallel and not cls.queue.empty():
                case_model: CaseModel = await cls.queue.get()
                cls.running_tasks += 1
                asyncio.create_task(cls.execute_task(case_model))

            now = time.time()
            time_diff = now - last_get_time


            # 空池 → 10秒拉一次
            if cls.running_tasks == 0:
                if time_diff >= 10:
                    await cls.get_case_task()
                    last_get_time = now

            # 未满（允许 +1 等待位）
            elif 0 < cls.running_tasks < allow_max:
                if time_diff >= 2:
                    await cls.get_case_task()
                    last_get_time = now

            # 满池 +1 已占 → 不拉
            elif cls.running_tasks >= allow_max:
                pass

    @classmethod
    async def get_case_task(cls):
        try:
            if settings.IS_OPEN:
                from src.network import ToolsSocketEnum, socket_conn
                from src import CacheKeyEnum
                from src.tools.set_config import SetConfig
                await socket_conn.async_send(
                    '请求获取任务',
                    func_name=ToolsSocketEnum.GET_TASK.value,
                    func_args=GetTaskModel(type=TestCaseTypeEnum.UI, username=SetConfig.get_username())
                )
        except Exception as error:
            log.error(f'get_case_task失败，类型：{type(error)}，失败详情：{error}，失败明细：{traceback.format_exc()}')

    @classmethod
    @async_memory
    async def execute_task(cls, case_model: CaseModel):
        try:
            async with TestCase(cls.parent, case_model, cls.driver_object) as obj:
                send_global_msg(f'开始执行UI测试用例：{case_model.name}')
                await obj.case_main()
        finally:
            cls.running_tasks -= 1

    @classmethod
    async def add_task(cls, case_model: CaseModel):
        await cls.queue.put(case_model)

    @classmethod
    def stop(cls):
        cls.running = False

    @classmethod
    def reset_driver_object(cls):
        cls.driver_object = DriverObject(log, True)
