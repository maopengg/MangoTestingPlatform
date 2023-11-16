# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-04-29 11:20
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_system.data_consumer.update_test_suite import TestSuiteReportUpdate
from PyAutoTest.auto_test.auto_ui.data_consumer.consumer_test_result import ConsumerTestResult
from PyAutoTest.models.socket_model.ui_model import PageStepsResultModel, CaseResult


class UIConsumer:

    def u_page_steps(self, data: dict):
        data = PageStepsResultModel(**data)
        ConsumerTestResult.page_step_status_update(data)

    def u_case_result(self, data: dict):
        data = CaseResult(**data)
        TestSuiteReportUpdate.update_case_suite_status(data.test_suite_id, data.status)
        ConsumerTestResult.update_case_status(data.case_id, data.status)
        ConsumerTestResult.update_case_result(data)


