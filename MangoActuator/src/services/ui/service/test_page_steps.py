# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2023/3/23 11:31
# @Author : 毛鹏
import asyncio
import traceback
from typing import Optional

from mangokit import singleton

from src.enums.system_enum import ClientTypeEnum
from src.exceptions import MangoActuatorError
from src.models import queue_notification
from src.models.ui_model import PageStepsModel, EquipmentModel
from src.network.web_socket.socket_api_enum import UiSocketEnum
from src.network.web_socket.websocket_client import WebSocketClient
from src.services.ui.bases.driver_object import DriverObject
from src.services.ui.service.page_steps import PageSteps
from src.tools.log_collector import log


@singleton
class TestPageSteps(PageSteps):
    """用例分发"""

    def __init__(self, parent, project_product):
        self.driver_object = DriverObject()
        self.parent = parent
        super().__init__(
            self.parent,
            self.driver_object,
            project_product
        )
        self.msg = ''
        self.page_step_model: Optional[PageStepsModel | None] = None
        self.lock = asyncio.Lock()

    async def page_init(self, data: PageStepsModel):
        self.page_step_model = data
        self.project_product_id = data.project_product
        self.equipment_config = data.equipment_config
        self.environment_config = data.environment_config
        self.is_step = True
        await self.public_front(self.page_step_model.public_data_list)

    async def page_steps_mian(self, data: PageStepsModel) -> None:
        await self.page_init(data)
        try:
            async with self.lock:
                await self.steps_init(self.page_step_model)
                await self.driver_init()
                await self.steps_main()
            await self.send_steps_result(
                200 if self.page_step_result_model.status else 300,
                f'步骤<{self.page_step_model.name}>测试完成' if self.page_step_result_model.status else f'步骤<{self.page_step_model.name}>测试失败，错误提示：{self.page_step_result_model.error_message}',
                self.page_step_result_model.status
            )
            self.finished.emit(True)
        except MangoActuatorError as error:
            await self.setup()
            await self.send_steps_result(error.code, error.msg, 0)
        except Exception as error:
            traceback.print_exc()
            log.error(error)
            await self.send_steps_result(
                300,
                f'执行步骤<{self.page_steps_model.name}>发生未知错误，请联系管理员，报错内容：{error}',
                self.page_step_result_model.status
            )

    async def new_web_obj(self, data: EquipmentModel):
        try:
            if self.page is None and self.context is None:
                await self.web_init(data)
                msg = 'WEB对象实例化成功，请手动输入对应选择的测试项目和部署环境的url进行访问开始录制！'
            else:
                msg = 'WEB对象已实例化'
            if self.page.is_closed():
                self.page = None
                self.context = None
                await self.web_init(data)
            await self.send_steps_result(200, msg, 1)

        except MangoActuatorError as error:
            await self.send_steps_result(error.code, error.msg, 0)
        except Exception as error:
            traceback.print_exc()
            log.error(error)
            msg = f'实例化浏览器发生未知错误，请联系管理员，报错内容：{error}'
            await self.send_steps_result(300, msg, 0)

    async def send_steps_result(self, code, msg, _type):
        await WebSocketClient().async_send(
            code=code,
            msg=msg,
            is_notice=ClientTypeEnum.WEB,
            func_name=UiSocketEnum.PAGE_STEPS.value,
            func_args=self.page_step_result_model
        )
        queue_notification.put({'type': _type, 'value': msg})
