# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2025-08-28 15:08
# @Author : 毛鹏
from mangotools.contracts import PytestExecutionResult
from mangotools.contracts import TestSuiteDetailResultContract

from src.apps.auto_pytest.services.test_report_writing import PtestTestReportWriting
from src.apps.test_center.schemas.execution import TestSuiteDetailResultSchema
from src.apps.test_center.services.test_suite.update_test_suite import UpdateTestSuite
from src.common.decorators.retry import async_task_db_connection


class PytestConsumer:

    @classmethod
    @async_task_db_connection()
    def p_test_suite_details(cls, data: dict):
        contract = TestSuiteDetailResultContract.model_validate(data)
        UpdateTestSuite.update_test_suite_details(TestSuiteDetailResultSchema.from_contract(contract))

    @classmethod
    @async_task_db_connection()
    def p_test_case(cls, data: dict):
        PtestTestReportWriting.update_pytest_test_case(PytestExecutionResult(**data))
