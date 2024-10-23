# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023/3/23 11:31
# @Author : 毛鹏
import asyncio
from typing import Optional

from mangokit import singleton

from src.enums.tools_enum import ClientTypeEnum
from src.exceptions import MangoActuatorError
from src.models import queue_notification
from src.models.ui_model import PageStepsModel, WEBConfigModel
from src.network.web_socket.socket_api_enum import UiSocketEnum
from src.network.web_socket.websocket_client import WebSocketClient
from src.services.ui.bases.driver_object import DriverObject
from src.services.ui.service.step_elements import StepElements


@singleton
class PageSteps(StepElements):
    """用例分发"""

    def __init__(self, ):
        self.driver_object = DriverObject()
        super().__init__(self.driver_object)
        self.msg = ''
        self.page_step_model: Optional[PageStepsModel | None] = None
        self.lock = asyncio.Lock()

    async def page_steps_setup(self, data: PageStepsModel):
        self.page_step_model: PageStepsModel = data
        self.project_product_id = data.project_product
        self.is_step = True
        await self.public_front(self.page_step_model.public_data_list)

    async def page_steps_mian(self, data: PageStepsModel) -> None:
        await self.page_steps_setup(data)
        try:
            async with self.lock:
                await self.steps_init(self.page_step_model)
                await self.driver_init()
                await self.steps_main()
        except MangoActuatorError as error:
            if error.code == 310:
                if self.context:
                    await self.context.close()
                if self.page:
                    await self.page.close()
                self.context = None
                self.page = None
            await WebSocketClient().async_send(
                code=error.code,
                msg=error.msg,
                is_notice=ClientTypeEnum.WEB
            )
            queue_notification.put({'type': 0, 'value': error.msg})
        else:
            msg = f'步骤<{self.page_step_model.name}>测试完成' if self.page_step_result_model.status else f'步骤<{self.page_step_model.name}>测试失败，错误提示：{self.page_step_result_model.error_message}'
            await WebSocketClient().async_send(
                code=200 if self.page_step_result_model.status else 300,
                msg=msg,
                is_notice=ClientTypeEnum.WEB,
                func_name=UiSocketEnum.PAGE_STEPS.value,
                func_args=self.page_step_result_model
            )
            queue_notification.put({'type': self.page_step_result_model.status, 'value': msg})
        self.finished.emit(True)

    async def new_web_obj(self, data: WEBConfigModel):
        msg = 'WEB对象已实例化'
        try:
            if self.page is None and self.context is None:
                await self.web_init(data)
                msg = 'WEB对象实例化成功，请手动输入对应选择的测试项目和部署环境的url进行访问开始录制！'
            # 检查页面是否已关闭
            if self.page.is_closed():
                self.page = None
                self.context = None
                await self.web_init(data)
        except MangoActuatorError as error:
            await WebSocketClient().async_send(
                msg=error.msg,
                code=error.code,
                is_notice=ClientTypeEnum.WEB
            )
            queue_notification.put({'type': 0, 'value': msg})

        else:
            await WebSocketClient().async_send(
                msg=msg,
                is_notice=ClientTypeEnum.WEB
            )
            queue_notification.put({'type': 1, 'value': msg})
