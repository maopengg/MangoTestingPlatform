# -*- coding: utf-8 -*-
# @Project: 
# @Description: 
# @Time   : 2025-02-22 下午4:34
# @Author : 毛鹏
import json
import os
import subprocess
import uuid

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
        report_path = fr'{project_dir.logs()}\{uuid.uuid4()}.json'
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

    def result_data(self, result_data, model):
        model.result_data = result_data
        model.status = 0 if result_data.get('summary').get('failed', None) is None else 1
        model.save()
        if self.test_suite and self.test_suite_details:
            UpdateTestSuite.update_test_suite_details(TestSuiteDetailsResultModel(
                id=self.test_suite_details,
                type=TestCaseTypeEnum.PYTEST,
                test_suite=self.test_suite,
                status=0 if result_data.get('summary').get('failed', None) is None else 1,
                error_message=None,
                result_data=result_data
            ))
