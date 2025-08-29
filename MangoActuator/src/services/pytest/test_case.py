# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2025-08-27 10:19
# @Author : 毛鹏
import traceback

from mangotools.mangos import GitPullManager, pytest_test_case

from src.enums.gui_enum import TipsTypeEnum
from src.enums.pytest_enum import PytestSystemEnum, AllureStatusEnum
from src.enums.system_enum import ClientTypeEnum
from src.enums.tools_enum import TaskEnum, TestCaseTypeEnum, StatusEnum
from src.models import queue_notification
from src.models.pytest_model import PytestCaseModel, PytestCaseResultModel
from src.models.system_model import TestSuiteDetailsResultModel
from src.network import socket_conn
from src.network.web_socket.socket_api_enum import PytestSocketEnum
from src.tools import project_dir
from src.tools.log_collector import log


class TestCase:

    def __init__(self, parent, case_model: PytestCaseModel):
        self.parent = parent
        self.case_model: PytestCaseModel = case_model
        self.case_result = PytestCaseResultModel(
            id=self.case_model.id,
            name=self.case_model.name,
            status=StatusEnum.SUCCESS.value,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        traceback.print_exc()
        return self

    async def test_case(self) -> list[dict]:
        log.debug(f'开始执行pytest用例：{self.case_model.name}')
        git = GitPullManager(self.case_model.git_url, project_dir.root_path(), log)
        git.clone()
        git.pull(self.case_model.commit_hash)
        report_data = pytest_test_case(
            allure=project_dir.allure(),
            log=log,
            test_env_name=PytestSystemEnum.TEST_ENV.value,
            test_env=self.case_model.test_env,
            file_path=self.case_model.file_path,
            quiet=True,
        )
        await self.result_data(report_data)
        await self.send_case_result()
        return report_data

    async def result_data(self, result_data: list[dict]):
        status = TaskEnum.SUCCESS.value
        for i in result_data:
            if i.get('status') != AllureStatusEnum.SUCCESS.value:
                i['status'] = TaskEnum.FAIL.value
                status = TaskEnum.FAIL.value
            else:
                i['status'] = TaskEnum.SUCCESS.value
        self.case_result.status = status
        self.case_result.result_data = result_data

    async def send_case_result(self):
        if self.case_model.test_suite_details and self.case_model.test_suite_id:
            func_name = PytestSocketEnum.TEST_CASE_BATCH.value
            func_args = TestSuiteDetailsResultModel(
                id=self.case_model.test_suite_details,
                type=TestCaseTypeEnum.UI,
                test_suite=self.case_model.test_suite_id,
                status=self.case_result.status,
                error_message=self.case_result.error_message,
                result_data=self.case_result,
            )
        else:
            func_name = PytestSocketEnum.TEST_CASE.value
            func_args = self.case_result
        await socket_conn.async_send(
            code=200 if self.case_result.status else 300,
            msg=f'pytest用例<{self.case_model.name}>测试完成',
            is_notice=ClientTypeEnum.WEB,
            func_name=func_name,
            func_args=func_args,
            user=self.case_model.send_user,
        )
        queue_notification.put({
            'type': TipsTypeEnum.SUCCESS if self.case_result.status else TipsTypeEnum.ERROR,
            'value': f'pytest用例<{self.case_model.name}>测试完成'
        })
