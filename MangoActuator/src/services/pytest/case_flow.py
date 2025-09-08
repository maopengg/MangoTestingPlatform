# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-08-27 10:19
# @Author : 毛鹏

import asyncio
import time
import traceback

from src.enums.tools_enum import TestCaseTypeEnum
from src.models.pytest_model import PytestCaseModel
from src.models.system_model import GetTaskModel
from src.services.pytest.test_case import TestCase
from src.settings import settings
from src.tools.log_collector import log
from src.tools.send_global_msg import send_global_msg


class PytestCaseFlow:
    queue = asyncio.Queue()
    max_tasks = 5
    running_tasks = 0
    parent = None
    running = True

    @classmethod
    async def process_tasks(cls):
        s = time.time()
        while cls.running:
            await asyncio.sleep(0.1)
            if cls.running_tasks < cls.max_tasks and not cls.queue.empty():  # type: ignore
                case_model: PytestCaseModel = await cls.queue.get()
                cls.running_tasks += 1
                asyncio.create_task(cls.execute_task(case_model))
            else:
                if time.time() - s > 5:
                    s = time.time()
                    await cls.get_case_task()

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
                    func_args=GetTaskModel(type=TestCaseTypeEnum.PYTEST, username=SetConfig.get_username())
                )
        except Exception as error:
            log.error(f'get_case_task失败，类型：{type(error)}，失败详情：{error}，失败明细：{traceback.format_exc()}')

    @classmethod
    async def execute_task(cls, case_model: PytestCaseModel):
        async with TestCase(cls.parent, case_model) as obj:
            send_global_msg(f'开始执行Pytest测试用例：{case_model.name}')
            await obj.test_case()
            cls.running_tasks -= 1

    @classmethod
    async def add_task(cls, case_model: PytestCaseModel):
        await cls.queue.put(case_model)

    @classmethod
    def stop(cls):
        cls.running = False
