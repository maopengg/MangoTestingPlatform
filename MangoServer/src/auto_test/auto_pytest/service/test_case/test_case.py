# -*- coding: utf-8 -*-
# @Project: 
# @Description: 
# @Time   : 2025-02-22 下午4:34
# @Author : 毛鹏
import json
import os
import subprocess
import uuid
from pathlib import Path

import pytest
from pytest_jsonreport.plugin import JSONReport

from src.auto_test.auto_pytest.models import PytestCase
from src.auto_test.auto_system.service.update_test_suite import UpdateTestSuite
from src.enums.tools_enum import TaskEnum, TestCaseTypeEnum
from src.models.system_model import TestSuiteDetailsResultModel
from src.tools import project_dir


class TestCase:

    def __init__(self, user_id=None, test_suite=None, test_suite_details=None):
        self.user_id = user_id
        self.test_suite = test_suite
        self.test_suite_details = test_suite_details

    def test_case_cmd(self, case_id) -> dict:
        obj = PytestCase.objects.get(id=case_id)
        obj.status = TaskEnum.PROCEED.value
        obj.save()
        report_path = os.path.join(project_dir.root_path(), f'{uuid.uuid4()}.json')

        subprocess.run(
            ['pytest', obj.file_path, '--json-report', f'--json-report-file={report_path}'],
            capture_output=True,
            text=True
        )
        with open(report_path, 'r') as f:
            report_data = json.load(f)
        os.remove(report_path)
        self.result_data(report_data, obj)
        return report_data

    def test_case_main(self, case_id) -> dict:
        obj = PytestCase.objects.get(id=case_id)
        obj.status = TaskEnum.PROCEED.value
        obj.save()
        plugin = JSONReport()
        pytest.main(
            ['--json-report-file=none', obj.file_path, '-q'],
            plugins=[plugin],
        )
        report_data = plugin.report
        self.result_data(report_data, obj)
        return report_data

    def result_data(self, result_data: dict | list, model):
        status = TaskEnum.SUCCESS.value if result_data.get('summary', {}).get('failed',
                                                                              None) is None else TaskEnum.FAIL.value
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
            ))

    def test_case_allure(self, case_id) -> list[dict]:
        obj = PytestCase.objects.get(id=case_id)
        obj.status = TaskEnum.PROCEED.value
        obj.save()
        allure_results_dir = os.path.join(project_dir.root_path(), f'allure-results-{uuid.uuid4()}')
        os.makedirs(allure_results_dir, exist_ok=True)

        # 运行 pytest 并生成 Allure JSON 报告
        subprocess.run(
            ['pytest', obj.file_path, '-q', '--alluredir', allure_results_dir],
            capture_output=True,
            text=True
        )

        # 读取 Allure JSON 报告
        report_data = self.read_allure_json_results(allure_results_dir)

        # 删除生成的 Allure 结果目录
        self.delete_allure_results(allure_results_dir)

        # 处理报告数据
        self.result_data(report_data, obj)
        return report_data

    def read_allure_json_results(self, results_dir):
        """
        读取 Allure JSON 报告文件并返回数据
        """
        report_data = []
        for json_file in Path(results_dir).glob('*.json'):
            with open(json_file, 'r') as f:
                report_data.append(json.load(f))
        return report_data

    def delete_allure_results(self, results_dir):
        """
        删除 Allure 结果目录
        """
        for json_file in Path(results_dir).glob('*.json'):
            os.remove(json_file)
        os.rmdir(results_dir)
