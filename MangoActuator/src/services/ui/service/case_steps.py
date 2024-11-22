# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2023/5/4 14:33
# @Author : 毛鹏

import asyncio
import json
import os
import shutil
import traceback

from mangokit import RandomTimeData

from src.enums.tools_enum import ClientTypeEnum
from src.enums.tools_enum import StatusEnum
from src.exceptions import *
from src.models import queue_notification
from src.models.ui_model import CaseModel, CaseResultModel
from src.network.web_socket.socket_api_enum import UiSocketEnum
from src.network.web_socket.websocket_client import WebSocketClient
from src.services.ui.service.step_elements import StepElements
from src.tools import InitPath
from src.tools.decorator.memory import async_memory
from src.tools.log_collector import log


class CaseSteps(StepElements):

    def __init__(self, case_model: CaseModel, driver_object):
        super().__init__(
            driver_object,
            project_product_id=case_model.project_product,
            test_suite_id=case_model.test_suite_id,
            case_id=case_model.id,
        )
        self.case_model: CaseModel = case_model
        self.case_result = CaseResultModel(
            test_suite_id=self.test_suite_id,
            case_id=self.case_id,
            case_name=self.case_model.name,
            module_name=self.case_model.module_name,
            case_people=self.case_model.case_people,
            status=StatusEnum.SUCCESS.value,
            page_steps_result_list=[]
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.base_close()
        if self.driver_object.web_config and self.driver_object.web_config.web_recording:
            video_path = f'{self.case_model.name}-{RandomTimeData.get_time_for_min()}.webm'
            shutil.move(self.case_result.video_path, os.path.join(f'{InitPath.videos}/', video_path))
            self.case_result.video_path = video_path

    async def case_init(self):
        await self.public_front(self.case_model.public_data_list)

    @async_memory
    async def case_page_step(self) -> None:
        try:
            await self.case_front(self.case_model.front_custom, self.case_model.front_sql)
            for steps in self.case_model.steps:
                try:
                    await self.steps_init(steps)
                    self.case_result.environment_id = self.environment_config.id
                    await self.driver_init()
                    page_steps_result_model = await self.steps_main()
                    self.case_result \
                        .page_steps_result_list \
                        .append(page_steps_result_model)
                    self.case_result.test_obj = self.url
                except MangoActuatorError as error:
                    self.case_result.error_message = f'用例<{self.case_model.name}> 失败原因：{error.msg}'
                    self.case_result.status = StatusEnum.FAIL.value
                    log.warning(error.msg)
                    break
                else:
                    if page_steps_result_model.status:
                        await asyncio.sleep(0.5)
                    else:
                        self.case_result.error_message = f'用例<{self.case_model.name}> 失败原因：{page_steps_result_model.error_message}'
                        self.case_result.status = StatusEnum.FAIL.value
                        log.warning(page_steps_result_model.error_message)
                        break
            self.case_result.test_obj = self.get_test_obj()
            await self.case_posterior(self.case_model.posterior_sql)
        except MangoActuatorError as error:
            self.case_result.error_message = f'用例<{self.case_model.name}> 失败原因：{error.msg}'
            self.case_result.status = StatusEnum.FAIL.value
        except Exception as error:
            traceback.print_exc()
            log.error(error)
            await WebSocketClient().async_send(
                code=200 if self.case_result.status else 300,
                msg='发生未知错误，请联系管理员检查测试用例数据',
                is_notice=ClientTypeEnum.WEB,
                func_name=UiSocketEnum.CASE_RESULT.value,
                func_args=self.case_result
            )
            queue_notification.put(
                {'type': self.case_result.status, 'value': '发生未知错误，请联系管理员检查测试用例数据'})
        else:
            msg = self.case_result.error_message if self.case_result.error_message else f'用例<{self.case_model.name}>测试完成'
            await WebSocketClient().async_send(
                code=200 if self.case_result.status else 300,
                msg=msg,
                is_notice=ClientTypeEnum.WEB,
                func_name=UiSocketEnum.CASE_RESULT.value,
                func_args=self.case_result
            )
            queue_notification.put({'type': self.case_result.status, 'value': msg})

    async def case_front(self, front_custom: list[dict], front_sql: list[dict]):
        for i in front_custom:
            self.test_case.set_cache(i.get('key'), i.get('value'))
        for i in front_sql:
            if self.mysql_connect:
                sql = self.test_case.replace(i.get('sql'))
                result_list: list[dict] = self.mysql_connect.condition_execute(sql)
                if isinstance(result_list, list):
                    for result in result_list:
                        try:
                            for value, key in zip(result, eval(i.get('value'))):
                                self.test_case.set_cache(key, result.get(value))
                        except SyntaxError:
                            raise ToolsError(*ERROR_MSG_0039)
                    if not result_list:
                        raise ToolsError(*ERROR_MSG_0037, value=(sql,))

    async def case_posterior(self, posterior_sql: list[dict]):
        for sql in posterior_sql:
            self.mysql_connect.condition_execute(sql.get('sql'))
        await self.sava_videos()

    async def sava_videos(self):
        if self.driver_object.web_config and self.driver_object.web_config.web_recording:
            self.case_result.video_path = await self.page.video.path()  # 获取视频的路径

    def get_test_obj(self):
        if self.url and self.package_name is None:
            return self.url
        if self.url is None and self.package_name:
            return self.package_name
        if self.url and self.package_name:
            return json.dumps([self.url, self.package_name])
