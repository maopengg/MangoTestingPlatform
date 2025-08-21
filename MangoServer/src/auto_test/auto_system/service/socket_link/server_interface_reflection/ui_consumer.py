# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-04-29 11:20
# @Author : 毛鹏

from src.auto_test.auto_system.service.update_test_suite import UpdateTestSuite
from src.auto_test.auto_ui.service.test_case.case_flow import UiCaseFlow
from src.auto_test.auto_ui.service.test_report_writing import TestReportWriting

from src.models.system_model import TestSuiteDetailsResultModel
from src.models.ui_model import PageStepsResultModel, UiCaseResultModel, GetTaskModel
from src.tools.decorator.retry import ensure_db_connection


class UIConsumer:

    @classmethod
    @ensure_db_connection()
    def u_page_steps(cls, data: dict):
        TestReportWriting.update_page_step_status(PageStepsResultModel(**data))

    @classmethod
    @ensure_db_connection()
    def u_test_suite_details(cls, data: dict):
        UpdateTestSuite.update_test_suite_details(TestSuiteDetailsResultModel(**data))

    @classmethod
    @ensure_db_connection()
    def u_test_case(cls, data: dict):
        TestReportWriting.update_test_case(UiCaseResultModel(**data))

    @classmethod
    @ensure_db_connection()
    def u_get_task(cls, data: dict):
        data = GetTaskModel(**data)
        UiCaseFlow.get_case(data)
