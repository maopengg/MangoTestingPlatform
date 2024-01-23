# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-04-29 11:20
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_system.service.update_test_suite import TestSuiteReportUpdate
from PyAutoTest.auto_test.auto_ui.service.test_report_writing import TestReportWriting
from PyAutoTest.models.socket_model.ui_model import PageStepsResultModel, TestSuiteModel, CaseResultModel
from PyAutoTest.tools.decorator.convert_args import convert_args


class UIConsumer:

    @convert_args(PageStepsResultModel)
    def u_page_steps(self, data: PageStepsResultModel):
        TestReportWriting.update_page_step_status(data)

    @convert_args(CaseResultModel)
    def u_case_result(self, data: CaseResultModel):
        TestReportWriting.update_case(data)

    @convert_args(TestSuiteModel)
    def u_case_batch_result(self, data: TestSuiteModel):
        TestSuiteReportUpdate.update_case_suite_status(data)

