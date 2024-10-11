# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023/5/10 11:43
# @Author : 毛鹏
import asyncio

from src.enums.tools_enum import ClientTypeEnum, CacheKeyEnum
from src.exceptions import MangoActuatorError
from src.models.ui_model import PageStepsModel, WEBConfigModel, CaseModel
from src.models.user_model import UserModel
from src.network.web_socket.websocket_client import WebSocketClient
from src.services.ui.service.case_main import CaseMain
from src.services.ui.service.page_steps import PageSteps
from src.tools.decorator.convert_args import convert_args
from src.tools.decorator.error_handle import async_error_handle


class UIConsumer:
    page_steps: PageSteps = None
    case_run: CaseMain = None
    lock = asyncio.Lock()

    @classmethod
    @async_error_handle()
    @convert_args(PageStepsModel)
    async def u_page_step(cls, data: PageStepsModel):
        """
        执行页面步骤
        @param data:
        @return:
        """
        try:
            async with cls.lock:
                if cls.page_steps is None:
                    cls.page_steps = PageSteps(data.project_product)
                await cls.page_steps.page_steps_setup(data)
                await cls.page_steps.page_steps_mian()
        except MangoActuatorError as error:
            await WebSocketClient().async_send(
                code=error.code,
                msg=error.msg,
                is_notice=ClientTypeEnum.WEB.value
            )

    @classmethod
    @async_error_handle()
    @convert_args(WEBConfigModel)
    async def u_page_new_obj(cls, data: WEBConfigModel):
        """
        实例化浏览器对象
        @param data:
        @return:
        """
        async with cls.lock:
            if cls.page_steps is None:
                cls.page_steps = PageSteps()
            await cls.page_steps.new_web_obj(data)

    @classmethod
    @async_error_handle()
    @convert_args(CaseModel)
    async def u_case(cls, data: CaseModel):
        """
        执行测试用例
        @param data:
        @return:
        """
        if cls.case_run is None:
            max_tasks = 5
            test_case_parallelism = UserModel().config.web_parallel
            if test_case_parallelism:
                max_tasks = int(test_case_parallelism)
            cls.case_run = CaseMain(max_tasks)
        await cls.case_run.queue.put(data)
