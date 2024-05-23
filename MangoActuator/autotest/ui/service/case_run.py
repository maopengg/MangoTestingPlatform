# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-04-26 10:53
# @Author : 毛鹏

import asyncio

from autotest.ui.base_tools.driver_object import DriverObject
from autotest.ui.service.cases import CasesMain
from enums.socket_api_enum import UiSocketEnum
from enums.ui_enum import DriveTypeEnum
from models.socket_model.ui_model import CaseModel
from tools.log_collector import log
from tools.public_methods import async_global_exception


class CaseRun(DriverObject):

    def __init__(self, max_tasks=10):
        super().__init__()
        self.queue = asyncio.Queue()
        self.max_tasks = max_tasks
        self.running_tasks = 0
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.process_tasks())

    async def process_tasks(self):
        while True:
            if self.running_tasks < self.max_tasks and not self.queue.empty():
                case_model = await self.queue.get()
                self.running_tasks += 1
                self.loop.create_task(self.execute_task(case_model))
            await asyncio.sleep(0.1)

    async def execute_task(self, case_model: CaseModel):
        async with CasesMain(case_model) as obj:
            try:
                for step in case_model.steps:
                    match step.type:
                        case DriveTypeEnum.WEB.value:
                            self.web_config = step.equipment_config
                            obj.context, obj.page = await self.new_web_page()
                            continue
                        case DriveTypeEnum.ANDROID.value:
                            self.android_config = step.equipment_config
                            obj.android = self.new_android()
                            continue
                        case DriveTypeEnum.IOS.value:
                            pass
                        case DriveTypeEnum.DESKTOP.value:
                            pass
                        case _:
                            log.error('自动化类型不存在，请联系管理员检查！')
                await obj.case_init()
                await obj.case_page_step()
            except Exception as error:
                await async_global_exception(
                    'execute_task',
                    error,
                    UiSocketEnum.CASE_RESULT.value,
                    obj.case_result
                )
            finally:
                self.running_tasks -= 1
