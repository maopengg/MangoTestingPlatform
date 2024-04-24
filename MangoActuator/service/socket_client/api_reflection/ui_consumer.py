# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023/5/10 11:43
# @Author : 毛鹏

from autotest.ui.service.page_steps import PageSteps
from autotest.ui.service.cases import Cases
from models.socket_model.ui_model import PageStepsModel, TestSuiteModel, WEBConfigModel
from tools.decorator.convert_args import convert_args


class UIConsumer:

    @classmethod
    @convert_args(PageStepsModel)
    async def u_page_step(cls, data: PageStepsModel):
        """
        执行页面步骤
        @param data:
        @return:
        """
        await PageSteps(data.project).debug_case_distribution(data)

    @classmethod
    @convert_args(WEBConfigModel)
    async def u_page_new_obj(cls, data: WEBConfigModel):
        """
        实例化浏览器对象
        @param data:
        @return:
        """
        await PageSteps(data.project).new_web_obj(data)

    @classmethod
    @convert_args(TestSuiteModel)
    async def u_case_batch(cls, data: TestSuiteModel):
        """
        执行测试用例
        @param data:
        @return:
        """
        await Cases(data).case_distribute()
