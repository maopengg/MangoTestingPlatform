# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-08-28 15:08
# @Author : 毛鹏
from src.auto_test.auto_pytest.service.test_report_writing import PtestTestReportWriting
from src.auto_test.auto_system.service.update_test_suite import UpdateTestSuite
from src.models.pytest_model import PytestCaseResultModel

from src.models.system_model import TestSuiteDetailsResultModel
from src.tools.decorator.retry import ensure_db_connection


class PytestConsumer:

    @classmethod
    # @ensure_db_connection()
    def p_test_suite_details(cls, data: dict):
        UpdateTestSuite.update_test_suite_details(TestSuiteDetailsResultModel(**data))

    @classmethod
    # @ensure_db_connection()
    def p_test_case(cls, data: dict):
        PtestTestReportWriting.update_pytest_test_case(PytestCaseResultModel(**data))
