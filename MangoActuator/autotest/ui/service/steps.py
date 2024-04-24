# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023/5/4 14:33
# @Author : 毛鹏

import asyncio

from autotest.ui.service.elements import Elements
from enums.socket_api_enum import UiSocketEnum
from enums.tools_enum import ClientTypeEnum
from enums.tools_enum import StatusEnum
from enums.ui_enum import DriveTypeEnum
from exceptions import MangoActuatorError
from models.socket_model.ui_model import CaseModel, CaseResultModel, PageStepsModel, PageStepsResultModel
from service.socket_client import ClientWebSocket
from tools.desktop.signal_send import SignalSend
from tools.log_collector import log


class Steps(Elements):
    case_model: CaseModel = None
    case_result: CaseResultModel = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.base_close()

    async def case_setup(self, case_model: CaseModel):
        self.case_model: CaseModel = case_model
        self.is_step = self.case_model.is_batch
        self.case_id = case_model.id
        self.case_result = CaseResultModel(test_suite_id=self.test_suite_id,
                                           is_batch=self.case_model.is_batch,
                                           case_id=self.case_model.id,
                                           case_name=self.case_model.name,
                                           module_name=self.case_model.module_name,
                                           case_people=self.case_model.case_people,
                                           error_message=None,
                                           test_obj=self.test_object_value,
                                           status=StatusEnum.SUCCESS.value,
                                           page_steps_result_list=[])
        await self.case_page_step()

    async def case_page_step(self) -> None:
        SignalSend.notice_signal_c(f'正在准备执行用例：{self.case_model.name}')
        try:
            if self.case_model.run_config:
                await self.public_front(self.case_model.run_config)
            await self.case_front(self.case_model.front_custom, self.case_model.front_sql)
            for page_step_model in self.case_model.case_list:
                try:
                    page_steps_result_model = await self.case_steps_distribute(page_step_model)
                    self.case_result.page_steps_result_list.append(page_steps_result_model)
                    self.case_result.test_obj = self.test_object_value
                except MangoActuatorError as error:
                    self.case_result.error_message = f'用例<{self.case_model.name}> 失败原因：{error.msg}'
                    self.case_result.status = StatusEnum.FAIL.value
                    log.error(error.msg)
                    break
                else:
                    if page_steps_result_model.status:
                        await asyncio.sleep(0.5)
                    else:
                        self.case_result.error_message = f'用例<{self.case_model.name}> 失败原因：{page_steps_result_model.error_message}'
                        self.case_result.status = StatusEnum.FAIL.value
                        log.error(page_steps_result_model.error_message)
                        break
            await self.case_posterior(self.case_model.posterior_sql)
        except MangoActuatorError as error:
            self.case_result.error_message = f'用例<{self.case_model.name}> 失败原因：{error.msg}'
            self.case_result.status = StatusEnum.FAIL.value
        except Exception as error:
            log.error(str(error))
            await ClientWebSocket.async_send(code=300,
                                             msg="执行元素步骤时发生未知异常，请检查数据或者联系管理员",
                                             is_notice=ClientTypeEnum.WEB.value)
        else:
            msg = self.case_result.error_message if self.case_result.error_message else f'用例<{self.case_model.name}>测试完成'
            await ClientWebSocket.async_send(
                code=200 if self.case_result.status else 300,
                msg=msg,
                is_notice=ClientTypeEnum.WEB.value,
                func_name=UiSocketEnum.CASE_RESULT.value,
                func_args=self.case_result)
        SignalSend.notice_signal_c(f'用例：{self.case_model.name} 执行完成！')

    async def case_steps_distribute(self, page_step_model: PageStepsModel) -> PageStepsResultModel:
        """
        分发用例方法，根据用例对象，来发给不同的对象来执行用例
        @return:
        """
        await self.steps_setup(page_step_model)
        await self.driver_init()
        return await self.steps_main()


if __name__ == '__main__':
    list__ = '["213","43132]'
    print(eval(list__))
