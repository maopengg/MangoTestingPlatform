# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023/3/23 11:31
# @Author : 毛鹏
from typing import Optional

from autotest.ui.service.step_elements import StepElements
from enums.socket_api_enum import UiSocketEnum
from enums.tools_enum import ClientTypeEnum
from exceptions import MangoActuatorError
from models.socket_model.ui_model import PageStepsModel, WEBConfigModel
from service.socket_client.client_socket import ClientWebSocket


class PageSteps(StepElements):
    """用例分发"""

    def __init__(self, project_product_id: int):
        super().__init__(project_product_id, )
        self.project_product_id = project_product_id
        self.msg = ''
        self.page_step_model: Optional[PageStepsModel | None] = None

    async def page_steps_setup(self, data: PageStepsModel):
        self.page_step_model: PageStepsModel = data
        self.project_product_id = self.page_step_model.project_product
        self.is_step = True
        await self.public_front(self.page_step_model.public_data_list)

    async def page_steps_mian(self) -> None:
        try:
            await self.steps_init(self.page_step_model)
            await self.driver_init()
            await self.steps_main()
        except MangoActuatorError as error:
            if error.code == 310:
                await self.context.close()
                await self.page.close()
                self.context = None
                self.page = None
            await ClientWebSocket().async_send(
                code=error.code,
                msg=error.msg,
                is_notice=ClientTypeEnum.WEB.value
            )
        else:
            await ClientWebSocket().async_send(
                code=200 if self.page_step_result_model.status else 300,
                msg=f'步骤<{self.page_step_model.name}>测试完成' if self.page_step_result_model.status else f'步骤<{self.page_step_model.name}>测试失败，错误提示：{self.page_step_result_model.error_message}',
                is_notice=ClientTypeEnum.WEB.value,
                func_name=UiSocketEnum.PAGE_STEPS.value,
                func_args=self.page_step_result_model
            )

    async def new_web_obj(self, data: WEBConfigModel):
        msg = 'WEB对象已实例化'
        if self.page is None and self.context is None:
            self.web_config = data
            self.context, self.page = await self.new_web_page()
            self.browser = self.browser
            msg = 'WEB对象实例化成功'
            if data.host:
                await self.w_goto(data.host)
        await ClientWebSocket().async_send(
            msg=msg,
            is_notice=ClientTypeEnum.WEB.value
        )
