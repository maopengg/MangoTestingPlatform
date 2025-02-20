# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2023/5/10 11:43
# @Author : 毛鹏
import asyncio

from src.enums.system_enum import ClientTypeEnum
from src.exceptions import MangoActuatorError
from src.models.ui_model import PageStepsModel, CaseModel, PageObject, EquipmentModel
from src.network.web_socket.websocket_client import WebSocketClient
from src.services.ui.service.case_flow import CaseFlow
from src.services.ui.service.test_page_steps import TestPageSteps
from src.tools.decorator.convert_args import convert_args


class UI:
    lock = asyncio.Lock()

    @convert_args(PageStepsModel)
    async def u_page_step(self, data: PageStepsModel):
        """
        执行页面步骤
        @param data:
        @return:
        """
        try:
            async with self.lock:
                if PageObject.test_page_steps is None:
                    PageObject.test_page_steps = TestPageSteps(self.parent, data.project_product)
                else:
                    PageObject.test_page_steps.project_product_id = data.project_product
                self.parent.set_tips_info(f'开始执行页面步骤：{data.name}')
                await PageObject.test_page_steps.page_steps_mian(data)
        except MangoActuatorError as error:
            await WebSocketClient().async_send(
                code=error.code,
                msg=error.msg,
                is_notice=ClientTypeEnum.WEB
            )

    @convert_args(EquipmentModel)
    async def u_page_new_obj(self, data: EquipmentModel):
        """
        实例化浏览器对象
        @param data:
        @return:
        """
        async with self.lock:
            if PageObject.test_page_steps is None:
                PageObject.test_page_steps = TestPageSteps(self.parent, None)
            self.parent.set_tips_info(f'开始打开浏览器')
            await PageObject.test_page_steps.new_web_obj(data)

    @convert_args(CaseModel)
    async def u_case(self, data: CaseModel):
        """
        执行测试用例
        @param data:
        @return:
        """
        max_tasks = next((i.equipment_config.web_parallel for i in data.steps if i and i.equipment_config), None)
        if PageObject.case_flow is None:
            PageObject.case_flow = CaseFlow(self.parent, max_tasks) if max_tasks else CaseFlow(self.parent)
        else:
            PageObject.case_flow.max_tasks = max_tasks
        if data.parametrize:
            for parametrize in data.parametrize:
                await PageObject.case_flow.add_task(data, parametrize)
        await PageObject.case_flow.add_task(data, None)
