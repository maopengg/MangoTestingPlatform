# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023/3/23 11:31
# @Author : 毛鹏
from autotest.ui.driver import NewDriverObject
from autotest.ui.test_runner.split_steps_elements import SplitStepsElements
from enums.socket_api_enum import UiSocketEnum
from enums.tools_enum import ClientTypeEnum
from enums.ui_enum import DriveTypeEnum
from exceptions import MangoActuatorError
from models.socket_model.ui_model import PageStepsModel, WEBConfigModel
from service.socket_client import ClientWebSocket
from tools.decorator.singleton import singleton
from tools.logging_tool import logger


@singleton
class PageSteps(SplitStepsElements):
    """
    用例分发
    """

    def __init__(self, project_id: int):
        super().__init__(project_id, )
        self.project_id = project_id
        self.msg = ''
        self.new_driver_object = NewDriverObject()

    async def debug_case_distribution(self, page_step_model: PageStepsModel) -> None:
        """
        处理调试用例，开始用例对象，并调用分发用例方法
        @param page_step_model:
        @return:
        """
        match page_step_model.type:
            case DriveTypeEnum.WEB.value:
                self.new_driver_object.web_config = page_step_model.equipment_config
                if not self.context and not self.page:
                    self.context, self.page = await self.new_driver_object.new_web_page()
                    # self.browser = self.new_driver_object.browser
            case DriveTypeEnum.ANDROID.value:
                pass
            case DriveTypeEnum.IOS.value:
                pass
            case DriveTypeEnum.DESKTOP.value:
                pass
            case _:
                logger.error('自动化类型不存在，请联系管理员检查！')

        try:
            self.is_step = True
            if page_step_model.run_config:
                await self.public_front(page_step_model.run_config)
            await self.steps_setup(page_step_model)
            await self.web_step()
        except MangoActuatorError as error:
            if error.code == 310:
                await self.context.close()
                await self.page.close()
                self.context = None
                self.page = None
            await ClientWebSocket.async_send(code=error.code,
                                             msg=error.msg,
                                             is_notice=ClientTypeEnum.WEB.value)
        else:
            await ClientWebSocket.async_send(
                code=200 if self.page_step_result_model.status else 300,
                msg=f'步骤<{page_step_model.name}>测试完成' if self.page_step_result_model.status else f'步骤<{page_step_model.name}>测试失败，错误提示：{self.page_step_result_model.error_message}',
                is_notice=ClientTypeEnum.WEB.value,
                func_name=UiSocketEnum.PAGE_STEPS.value,
                func_args=self.page_step_result_model
            )

    async def new_web_obj(self, data: WEBConfigModel):
        if self.page is None and self.context is None:
            self.new_driver_object.web_config = data
            self.context, self.page = await self.new_driver_object.new_web_page()
            self.browser = self.new_driver_object.browser
            self.msg = 'WEB对象实例化成功'
            if data.host:
                await self.w_goto(data.host)
        else:
            self.msg = 'WEB对象已实例化'
        await ClientWebSocket.async_send(msg=self.msg,
                                         is_notice=ClientTypeEnum.WEB.value)
