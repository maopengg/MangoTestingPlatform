# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-04-29 11:20
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_system.data_consumer.update_test_suite import TestSuiteReportUpdate
from PyAutoTest.auto_test.auto_ui.data_consumer.consumer_test_result import ConsumerTestResult
from PyAutoTest.models.socket_model.ui_model import PageStepsResultModel, TestSuiteModel, CaseResultModel
from PyAutoTest.tools.decorator.convert_args import convert_args


class UIConsumer:

    @convert_args(PageStepsResultModel)
    def u_page_steps(self, data: PageStepsResultModel):
        ConsumerTestResult.page_step_status_update(data)

    @convert_args(CaseResultModel)
    def u_case_result(self, data: CaseResultModel):
        TestSuiteReportUpdate.update_case_suite_status(data.test_suite_id, data.status)
        ConsumerTestResult.update_case_status(data.case_id, data.status)
        ConsumerTestResult.update_case_result(data)

    @convert_args(TestSuiteModel)
    def u_case_batch_result(self, data: TestSuiteModel):
        TestSuiteReportUpdate.update_case_suite_status(data.id, data.status, data.run_status, data.error_message)
        for i in data.result_list:
            ConsumerTestResult.update_case_status(i.case_id, data.result_list[0].status)
            ConsumerTestResult.update_case_result(i, data.error_message)
