# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2023/5/4 14:33
# @Author : 毛鹏

import json
import os
import shutil

from mangokit import RandomTimeData

from src.enums.gui_enum import TipsTypeEnum
from src.enums.system_enum import ClientTypeEnum
from src.enums.tools_enum import StatusEnum, AutoTestTypeEnum
from src.exceptions import *
from src.models import queue_notification
from src.models.system_model import TestSuiteDetailsResultModel
from src.models.ui_model import CaseModel, UiCaseResultModel, PageStepsResultModel
from src.network.web_socket.socket_api_enum import UiSocketEnum
from src.network.web_socket.websocket_client import WebSocketClient
from src.services.ui.service.page_steps import PageSteps
from src.tools import project_dir
from src.tools.decorator.error_handle import async_error_handle
from src.tools.decorator.memory import async_memory
from src.tools.log_collector import log


class TestCase(PageSteps):

    def __init__(self, parent, case_model: CaseModel, driver_object):
        super().__init__(
            parent,
            driver_object,
            project_product_id=case_model.project_product,
            test_suite_id=case_model.test_suite_id,
            case_id=case_model.id,
        )
        self.case_model: CaseModel = case_model
        self.case_result = UiCaseResultModel(
            id=self.case_model.id,
            name=self.case_model.name,
            project_product_id=self.case_model.project_product,
            project_product_name=self.case_model.project_product_name,
            module_name=self.case_model.module_name,
            test_env=self.case_model.test_env,
            status=StatusEnum.SUCCESS.value,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.base_close()
        if self.driver_object.web.config and self.driver_object.web.config.web_recording:
            video_path = f'{self.case_model.name}-{RandomTimeData.get_time_for_min()}.webm'
            shutil.move(self.case_result.video_path, os.path.join(f'{project_dir.videos()}/', video_path))
            self.case_result.video_path = video_path

    async def case_init(self):
        await self.public_front(self.case_model.public_data_list)

    @async_error_handle()
    @async_memory
    async def case_page_step(self) -> None:
        try:
            await self.case_front(self.case_model.front_custom, self.case_model.front_sql)
        except Exception as error:
            self.case_result.status = StatusEnum.FAIL.value
            await self.send_case_result(f'初始化用例前置数据发生未知异常，请联系管理员来解决!')
            raise error
        try:
            for steps in self.case_model.steps:
                await self.steps_init(steps)
                await self.driver_init()
                page_steps_result_model = await self.steps_main()
                self.case_result \
                    .steps \
                    .append(page_steps_result_model)
            await self.case_posterior(self.case_model.posterior_sql)
            await self.send_case_result(f'用例<{self.case_model.name}>测试完成')
        except MangoActuatorError as error:
            log.warning(error.msg)
            self.set_page_steps(self.page_step_result_model, error.msg)
            await self.send_case_result(error.msg)
        except Exception as error:
            self.set_page_steps(self.page_step_result_model,
                                f'执行用例发生未知错误，请联系管理员检查测试用例数据{error}')
            await self.send_case_result(self.case_result.error_message)
            raise error

    async def case_front(self, front_custom: list[dict], front_sql: list[dict]):
        for i in front_custom:
            self.test_data.set_cache(i.get('key'), i.get('value'))
        for i in front_sql:
            if self.mysql_connect:
                sql = self.test_data.replace(i.get('sql'))
                result_list: list[dict] = self.mysql_connect.condition_execute(sql)
                if isinstance(result_list, list):
                    for result in result_list:
                        try:
                            for value, key in zip(result, eval(i.get('value'))):
                                self.test_data.set_cache(key, result.get(value))
                        except SyntaxError:
                            raise ToolsError(*ERROR_MSG_0039)
                    if not result_list:
                        raise ToolsError(*ERROR_MSG_0037, value=(sql,))

    async def case_posterior(self, posterior_sql: list[dict]):
        for sql in posterior_sql:
            if self.mysql_connect and sql.get('sql', None) is not None:
                self.mysql_connect.condition_execute(sql.get('sql'))
        await self.sava_videos()

    async def sava_videos(self):
        if self.driver_object.web.config and self.driver_object.web.config.web_recording:
            self.case_result.video_path = await self.page.video.path()  # 获取视频的路径

    def get_test_obj(self):
        if self.url and self.package_name is None:
            return self.url
        if self.url is None and self.package_name:
            return self.package_name
        if self.url and self.package_name:
            return json.dumps([self.url, self.package_name])

    async def send_case_result(self, msg):
        if self.case_model.test_suite_details and self.case_model.test_suite_id:
            func_name = UiSocketEnum.TEST_CASE_BATCH.value
            func_args = TestSuiteDetailsResultModel(
                id=self.case_model.test_suite_details,
                type=AutoTestTypeEnum.UI,
                test_suite=self.case_model.test_suite_id,
                status=self.case_result.status,
                error_message=self.case_result.error_message,
                result_data=self.case_result
            )
        else:
            func_name = UiSocketEnum.TEST_CASE.value
            func_args = self.case_result
        await WebSocketClient().async_send(
            code=200 if self.case_result.status else 300,
            msg=msg,
            is_notice=ClientTypeEnum.WEB,
            func_name=func_name,
            func_args=func_args
        )
        queue_notification.put({
            'type': TipsTypeEnum.SUCCESS.value if self.case_result.status else TipsTypeEnum.ERROR.value,
            'value': msg
        })

    def set_page_steps(self, page_steps_result_model: PageStepsResultModel, msg: str):
        self.case_result.error_message = msg
        self.case_result.status = StatusEnum.FAIL.value
        self.case_result \
            .steps \
            .append(page_steps_result_model)
