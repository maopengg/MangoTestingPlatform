# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023/5/10 11:43
# @Author : 毛鹏
import asyncio

from src.models.ui_model import PageStepsModel, CaseModel, RecordingModel
from src.services.ui.case_flow import CaseFlow
from src.services.ui.test_page_steps import TestPageSteps
from src.tools.decorator.convert_args import convert_args
from src.tools.send_global_msg import send_global_msg

class UI:
    lock = asyncio.Lock()
    parent = None

    @classmethod
    @convert_args(PageStepsModel)
    async def u_page_step(cls, data: PageStepsModel):
        async with cls.lock:
            test_page_steps = TestPageSteps(cls.parent, data.project_product)
            send_global_msg(f'开始执行页面步骤：{data.name}')
            await test_page_steps.page_steps_mian(data)

    @classmethod
    async def u_page_new_obj(cls):
        async with cls.lock:
            test_page_steps = TestPageSteps(cls.parent, None)
            send_global_msg(f'开始打开浏览器')
            await test_page_steps.new_web_obj()

    @classmethod
    @convert_args(RecordingModel)
    async def u_recording(cls, data):
        async with cls.lock:
            test_page_steps = TestPageSteps(cls.parent, None)
            send_global_msg(f'开始准备录制，请手动访问需要录制的网页')
            await test_page_steps.new_web_obj(data)

    @classmethod
    @convert_args(CaseModel)
    async def u_case(cls, data: CaseModel):
        await CaseFlow.add_task(data)
