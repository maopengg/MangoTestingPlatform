# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2025-08-27 10:19
# @Author : 毛鹏
import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

import sys
from mangotools.mangos import GitRepoOperator

from src.enums.pytest_enum import PytestSystemEnum, AllureStatusEnum
from src.enums.system_enum import ClientTypeEnum
from src.enums.tools_enum import TaskEnum, TestCaseTypeEnum, StatusEnum, MessageEnum
from src.models.pytest_model import PytestCaseModel, PytestCaseResultModel
from src.models.system_model import TestSuiteDetailsResultModel
from src.network import socket_conn
from src.network.web_socket.socket_api_enum import PytestSocketEnum
from src.settings import settings
from src.tools import project_dir
from src.tools.log_collector import log
from src.tools.send_global_msg import send_global_msg


class TestCase:

    def __init__(self, parent, case_model: PytestCaseModel):
        self.parent = parent
        self.case_model: PytestCaseModel = case_model
        self.case_result = PytestCaseResultModel(
            id=self.case_model.id,
            name=self.case_model.name,
            status=StatusEnum.SUCCESS.value,
        )
        send_global_msg(self.case_model.name, MessageEnum.CASE_NAME)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return self

    async def test_case(self) -> list[dict]:
        log.debug(f'开始执行pytest用例：{self.case_model.model_dump_json()}')
        git = GitRepoOperator(
            self.case_model.git_url,
            project_dir.root_path(),
            log,
            self.case_model.git_username,
            self.case_model.git_password
        )
        send_global_msg(f'开始pytest的文件：{self.case_model.file_path}')
        git.clone()
        git.pull(self.case_model.commit_hash)
        report_data = self.pytest_test_case(
            allure=project_dir.allure(),
            log=log,
            test_env_name=PytestSystemEnum.TEST_ENV.value,
            test_env=self.case_model.test_env,
            file_path=os.path.normpath(self.case_model.file_path),
            quiet=settings.IS_DEBUG,
        )
        await self.result_data(report_data)
        await self.send_case_result()
        log.debug(f'pytest测试结果：{self.case_result.model_dump_json()}')
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
                type=TestCaseTypeEnum.PYTEST,
                test_suite=self.case_model.test_suite_id,
                status=self.case_result.status,
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
        send_global_msg(f'pytest用例<{self.case_model.name}>测试完成')

    def pytest_test_case(self, **kwargs):
        """
        使用子进程执行 pytest
        """

        allure_results_dir = os.path.join(
            kwargs.get('allure'),
            f'allure-results-{uuid.uuid4()}'
        )

        kwargs.get('log').debug(f'生成的用例存储目录：{allure_results_dir}')
        os.makedirs(allure_results_dir, exist_ok=True)

        # 设置环境变量
        env = os.environ.copy()
        env[kwargs.get('test_env_name')] = f'{kwargs.get("test_env")}'

        pytest_cmd = [
            sys.executable,  # 当前虚拟环境 python
            "-m",
            "pytest",
            os.path.abspath(kwargs.get('file_path')),
            "--alluredir",
            allure_results_dir
        ]

        if kwargs.get('quiet'):
            pytest_cmd.append("-q")
        if kwargs.get('verbose'):
            pytest_cmd.append("-v")
        if kwargs.get('show_output'):
            pytest_cmd.append("-s")

        kwargs.get('log').debug(f"启动 pytest 子进程命令: {pytest_cmd}")

        process = subprocess.Popen(
            pytest_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        stdout, stderr = process.communicate()

        kwargs.get('log').debug(f"pytest标准输出：\n{stdout}")
        kwargs.get('log').debug(f"pytest标准错误：\n{stderr}")
        kwargs.get('log').debug(f"pytest退出代码：{process.returncode}")
        report_data = self.read_allure_json_results(allure_results_dir)
        self.delete_allure_results(allure_results_dir)
        return report_data

    def read_allure_json_results(self, results_dir):
        report_data = []
        for json_file in Path(results_dir).glob('*-result.json'):
            with open(json_file, 'r', encoding='utf-8') as f:
                res_dict = json.load(f)
                for i in res_dict.get('attachments', []):
                    try:
                        with open(os.path.join(results_dir, i.get('source')), 'r', encoding='utf-8') as text:
                            content = text.read()
                            i['source'] = content
                    except FileNotFoundError:
                        i['source'] = '用例执行失败，这一项没有生成内容，所以没有结果'
                report_data.append(res_dict)
        return report_data

    def delete_allure_results(self, results_dir):
        if os.path.exists(results_dir):
            shutil.rmtree(results_dir)
