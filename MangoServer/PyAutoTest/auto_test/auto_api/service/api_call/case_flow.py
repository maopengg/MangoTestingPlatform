# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-23 20:38
# @Author : 毛鹏
import asyncio

from PyAutoTest.auto_test.auto_api.service.api_call.test_case import TestCase
from PyAutoTest.models.api_model import ApiCaseModel


class CaseFlow:
    queue = asyncio.Queue()
    max_tasks = 5
    running_tasks = 0
    loop = None

    @classmethod
    async def process_tasks(cls):
        while True:
            if cls.running_tasks < cls.max_tasks and not cls.queue.empty():
                case_model = await cls.queue.get()
                cls.running_tasks += 1
                asyncio.create_task(cls.execute_task(case_model))
            await asyncio.sleep(0.1)

    @classmethod
    async def execute_task(cls, case_model: ApiCaseModel):
        print(case_model)
        async with TestCase(case_model) as obj:
            await obj.case_main()
        cls.running_tasks -= 1

    @classmethod
    def add_task(cls, case_model: ApiCaseModel):
        cls.loop.create_task(cls.queue.put(case_model))
