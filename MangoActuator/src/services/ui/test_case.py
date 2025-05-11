# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2023/5/4 14:33
# @Author : 毛鹏

import os
import shutil
import traceback
from datetime import datetime

from mangokit.data_processor import RandomTimeData
from mangokit.exceptions import MangoKitError
from mangokit.uidrive import DriverObject, BaseData

from src.enums.gui_enum import TipsTypeEnum
from src.enums.system_enum import ClientTypeEnum
from src.enums.tools_enum import StatusEnum, TestCaseTypeEnum
from src.enums.ui_enum import UiPublicTypeEnum
from src.exceptions import *
from src.models import queue_notification
from src.models.system_model import TestSuiteDetailsResultModel
from src.models.ui_model import CaseModel, PageStepsResultModel, UiCaseResultModel
from src.network import socket_conn
from src.network.web_socket.socket_api_enum import UiSocketEnum
from src.services.ui.page_steps import PageSteps
from src.tools import project_dir
from src.tools.decorator.error_handle import async_error_handle
from src.tools.decorator.memory import async_memory
from src.tools.log_collector import log
from src.tools.obtain_test_data import ObtainTestData


class TestCase:

    def __init__(self, parent, case_model: CaseModel, driver_object: DriverObject):
        self.parent = parent
        self.case_model: CaseModel = case_model
        self.driver_object: DriverObject = driver_object
        self.test_data = ObtainTestData()
        self.base_data = BaseData(self.test_data, log) \
            .set_step_open_url(case_model.switch_step_open_url) \
            .set_file_path(project_dir.download(), project_dir.screenshot(), project_dir.videos())

        self.case_result = UiCaseResultModel(
            id=self.case_model.id,
            name=self.case_model.name,
            project_product_id=self.case_model.project_product,
            project_product_name=self.case_model.project_product_name,
            module_name=self.case_model.module_name,
            test_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            test_env=self.case_model.test_env,
            status=StatusEnum.SUCCESS.value,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.base_data.async_base_close()
        if self.driver_object.web.web_recording:
            video_path = f'{self.case_model.name}-{RandomTimeData.get_time_for_min()}.webm'
            shutil.move(self.case_result.video_path, os.path.join(f'{project_dir.videos()}/', video_path))
            self.case_result.video_path = video_path

    async def case_init(self):
        for cache_data in self.case_model.public_data_list:
            if cache_data.type == UiPublicTypeEnum.CUSTOM.value:
                self.test_data.set_cache(cache_data.key, cache_data.value)
            elif cache_data.type == UiPublicTypeEnum.SQL.value:
                if self.base_data.mysql_connect:
                    sql = self.test_data.replace(cache_data.value)
                    result_list: list[dict] = self.base_data.mysql_connect.condition_execute(sql)
                    if isinstance(result_list, list):
                        for result in result_list:
                            try:
                                for value, key in zip(result, eval(cache_data.key)):
                                    self.test_data.set_cache(key, result.get(value))
                            except SyntaxError as error:
                                log.error(
                                    f'初始化用例数据失败，类型：{type(error)}，失败详情：{error}，失败明细：{traceback.format_exc()}')
                                raise UiError(*ERROR_MSG_0038)

                        if not result_list:
                            raise UiError(*ERROR_MSG_0036, value=(sql,))

    @async_error_handle()
    @async_memory
    async def case_page_step(self) -> None:
        try:
            await self.case_front(self.case_model.front_custom, self.case_model.front_sql)
            await self.case_parametrize()
        except Exception as error:
            log.error(f'步骤初始化失败，类型：{error}，错误详情：{traceback.format_exc()}')
            self.case_result.status = StatusEnum.FAIL.value
            await self.send_case_result(f'初始化用例前置数据发生未知异常，请联系管理员来解决!')
            raise error
        for steps in self.case_model.steps:
            page_steps = PageSteps(self.base_data, self.driver_object, steps)
            try:
                await page_steps.driver_init()
                page_steps_result_model = await page_steps.steps_main()
                self.set_page_steps(page_steps_result_model)
                if page_steps_result_model.status == StatusEnum.FAIL.value:
                    break
            except (MangoActuatorError, MangoKitError) as error:
                log.debug(f'测试用例失败，类型：{type(error)}，失败详情：{error}')
                self.set_page_steps(page_steps.page_step_result_model)
                break
            except Exception as error:
                from mangokit.mangos import Mango  # type: ignore
                Mango.s(self.case_page_step, error, traceback.format_exc(), SetConfig.get_username())  # type: ignore
                log.error(f'测试用例失败，类型：{type(error)}，失败详情：{error}，失败明细：{traceback.format_exc()}')
                self.set_page_steps(page_steps.page_step_result_model,
                                    f'执行用例发生未知错误，请联系管理员检查测试用例数据，未知异常：{error}')
                break
        try:
            await self.send_case_result(
                f'用例<{self.case_model.name}>执行{f"失败，错误提示：{self.case_result.error_message}" if self.case_result.status == StatusEnum.FAIL.value else "通过"}')
            await self.case_posterior(self.case_model.posterior_sql)
            await self.sava_videos()
        except Exception:
            await self.send_case_result(
                f'用例:<{self.case_model.name}>后置处理失败了，如果是因为开启视频录制则忽略，开启视频录制需要安装：playwright install ffmpeg，或者请联系管理员来解决!')

    async def case_front(self, front_custom: list[dict], front_sql: list[dict]):
        front_custom = self.base_data.test_data.replace(front_custom)
        front_sql = self.base_data.test_data.replace(front_sql)
        for i in front_custom:
            self.base_data.test_data.set_cache(i.get('key'), i.get('value'))
        for i in front_sql:
            if self.base_data.mysql_connect:
                sql = self.base_data.test_data.replace(i.get('sql'))
                result_list: list[dict] = self.base_data.mysql_connect.condition_execute(sql)
                if isinstance(result_list, list):
                    for result in result_list:
                        try:
                            for value, key in zip(result, eval(i.get('value'))):
                                self.base_data.test_data.set_cache(key, result.get(value))
                        except SyntaxError as error:
                            log.error(
                                f'初始化用例数据失败，类型：{type(error)}，失败详情：{error}，失败明细：{traceback.format_exc()}')
                            raise ToolsError(*ERROR_MSG_0039)
                    if not result_list:
                        raise ToolsError(*ERROR_MSG_0037, value=(sql,))

    async def case_parametrize(self):
        if self.case_model.parametrize:
            for i in self.case_model.parametrize:
                self.base_data.test_data.set_cache(i.get('key'), self.base_data.test_data.replace(i.get('value')))

    async def case_posterior(self, posterior_sql: list[dict]):
        for sql in posterior_sql:
            if self.base_data.mysql_connect and sql.get('sql', None) is not None:
                self.base_data.mysql_connect.condition_execute(sql.get('sql'))

    async def sava_videos(self):
        if self.driver_object.web and self.driver_object.web.web_recording:
            self.case_result.video_path = await self.base_data.page.video.path()

    async def send_case_result(self, msg):
        if self.case_model.test_suite_details and self.case_model.test_suite_id:
            func_name = UiSocketEnum.TEST_CASE_BATCH.value
            func_args = TestSuiteDetailsResultModel(
                id=self.case_model.test_suite_details,
                type=TestCaseTypeEnum.UI,
                test_suite=self.case_model.test_suite_id,
                status=self.case_result.status,
                error_message=self.case_result.error_message,
                result_data=self.case_result
            )
        else:
            func_name = UiSocketEnum.TEST_CASE.value
            func_args = self.case_result
        await socket_conn.async_send(
            code=200 if self.case_result.status else 300,
            msg=msg,
            is_notice=ClientTypeEnum.WEB,
            func_name=func_name,
            func_args=func_args
        )
        queue_notification.put({
            'type': TipsTypeEnum.SUCCESS if self.case_result.status else TipsTypeEnum.ERROR,
            'value': msg
        })

    def set_page_steps(self, page_steps_result_model: PageStepsResultModel, msg=None):
        if msg:
            self.case_result.error_message = msg
            self.case_result.status = StatusEnum.FAIL.value
        else:
            self.case_result.status = page_steps_result_model.status
            self.case_result.error_message = page_steps_result_model.error_message
        self.case_result.steps.append(page_steps_result_model)
