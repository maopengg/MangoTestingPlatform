# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-04-29 11:20
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_system.service.update_test_suite import UpdateTestSuite
from PyAutoTest.auto_test.auto_ui.service.test_report_writing import TestReportWriting
from PyAutoTest.models.system_model import TestSuiteDetailsResultModel
from PyAutoTest.models.ui_model import PageStepsResultModel, CaseResultModel
from PyAutoTest.tools.decorator.convert_args import convert_args


class UIConsumer:

    @classmethod
    @convert_args(PageStepsResultModel)
    def u_page_steps(cls, data: PageStepsResultModel):
        TestReportWriting.update_page_step_status(data)

    @classmethod
    @convert_args(TestSuiteDetailsResultModel)
    def u_test_suite_details(cls, data: TestSuiteDetailsResultModel):
        UpdateTestSuite.update_test_suite_details(data)

    @classmethod
    @convert_args(CaseResultModel)
    def u_test_case(cls, data: CaseResultModel):
        TestReportWriting.update_test_case(data)
