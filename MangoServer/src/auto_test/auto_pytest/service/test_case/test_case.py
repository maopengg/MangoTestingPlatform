# -*- coding: utf-8 -*-
# @Project: 
# @Description: 
# @Time   : 2025-02-22 下午4:34
# @Author : 毛鹏
import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

from src.auto_test.auto_pytest.models import PytestCase
from src.auto_test.auto_system.service.update_test_suite import UpdateTestSuite
from src.enums.pytest_enum import AllureStatusEnum
from src.enums.tools_enum import TaskEnum, TestCaseTypeEnum
from src.models.system_model import TestSuiteDetailsResultModel
from src.tools import project_dir
from src.tools.log_collector import log


class TestCase:

    def __init__(self, user_id=None, test_suite=None, test_suite_details=None):
        self.user_id = user_id
        self.test_suite = test_suite
        self.test_suite_details = test_suite_details

    def test_case_main(self, case_id) -> list[dict]:
        obj = PytestCase.objects.get(id=case_id)
        obj.status = TaskEnum.PROCEED.value
        obj.save()
        allure_results_dir = os.path.join(project_dir.logs(), f'allure-results-{uuid.uuid4()}')
        os.makedirs(allure_results_dir, exist_ok=True)
        pytest_cmd = [
            'pytest',
            obj.file_path,
            '-q',
            # '-p', 'no:warnings',
            '--alluredir', allure_results_dir
        ]
        log.pytest.debug('启动命令：{}'.format(pytest_cmd))
        subprocess.run(pytest_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        report_data = self.read_allure_json_results(allure_results_dir)
        log.pytest.debug(f'{obj.name}测试结果：{report_data}')
        self.result_data(report_data, obj)
        self.delete_allure_results(allure_results_dir)
        return report_data

    def result_data(self, result_data: list[dict], model):
        status = TaskEnum.SUCCESS.value
        for i in result_data:
            if i.get('status') != AllureStatusEnum.SUCCESS.value:
                i['status'] = TaskEnum.FAIL.value
                status = TaskEnum.FAIL.value
            else:
                i['status'] = TaskEnum.SUCCESS.value

        model.result_data = result_data
        model.status = status
        model.save()
        if self.test_suite and self.test_suite_details:
            UpdateTestSuite.update_test_suite_details(TestSuiteDetailsResultModel(
                id=self.test_suite_details,
                type=TestCaseTypeEnum.PYTEST,
                test_suite=self.test_suite,
                status=status,
                error_message=None,
                result_data=result_data
            ), case_name=model.name)

    def read_allure_json_results(self, results_dir):
        """
        读取 Allure JSON 报告文件并返回数据
        """
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
        """
        删除 Allure 结果目录
        """
        if os.path.exists(results_dir):  # 检查目录是否存在
            shutil.rmtree(results_dir)  # 递归删除目录及其所有内容
