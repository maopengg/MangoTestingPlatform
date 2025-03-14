# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-04-26 10:53
# @Author : 毛鹏

import asyncio

from src.models.ui_model import CaseModel
from src.services.ui.service.test_case import TestCase
from src.tools.decorator.memory import async_memory
from ..bases.driver_object import DriverObject


class CaseFlow:

    def __init__(self, parent, max_tasks=2):
        super().__init__()
        self.queue = asyncio.Queue()
        self.max_tasks = max_tasks
        self.running_tasks = 0
        self.parent = parent
        self.parent.loop.create_task(self.process_tasks())
        self.driver_object = DriverObject()

    async def process_tasks(self):
        while True:
            if self.running_tasks < self.max_tasks and not self.queue.empty():
                case_model: dict = await self.queue.get()
                self.running_tasks += 1
                asyncio.create_task(self.execute_task(**case_model))
            await asyncio.sleep(0.1)

    @async_memory
    async def execute_task(self, case_model: CaseModel, parametrize):
        async with TestCase(self.parent, case_model, self.driver_object, parametrize) as obj:
            self.parent.set_tips_info(f'开始执行UI测试用例：{case_model.name}')
            await obj.case_init()
            await obj.case_page_step()
        self.running_tasks -= 1

    async def add_task(self, case_model: CaseModel, parametrize):
        await self.queue.put({'case_model': case_model, 'parametrize': parametrize})
