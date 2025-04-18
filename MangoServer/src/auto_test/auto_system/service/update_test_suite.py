# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-25 15:04
# @Author : 毛鹏
from django.db import connection

from src.auto_test.auto_system.models import TestSuite, TestSuiteDetails
from src.auto_test.auto_system.service.notice import NoticeMain
from src.auto_test.auto_ui.service.test_report_writing import TestReportWriting
from src.enums.system_enum import ClientTypeEnum
from src.enums.tools_enum import TaskEnum, StatusEnum, TestCaseTypeEnum
from src.models.socket_model import SocketDataModel
from src.models.system_model import TestSuiteDetailsResultModel
from src.tools.decorator.retry import orm_retry
from src.tools.log_collector import log


class UpdateTestSuite:
    @classmethod
    @orm_retry('update_case')
    def update_test_suite(cls, test_suite_id: int, status: int):
        connection.ensure_connection()
        test_suite = TestSuite.objects.get(id=test_suite_id)
        test_suite.status = status
        test_suite.save()

    @classmethod
    @orm_retry('update_test_suite')
    def update_test_suite_details(cls, data: TestSuiteDetailsResultModel, case_name=None):
        connection.ensure_connection()
        log.system.debug(f'开始更新测试套数据：{data.model_dump_json()}')
        test_suite_detail = TestSuiteDetails.objects.get(id=data.id)
        if data.type == TestCaseTypeEnum.UI or data.type == TestCaseTypeEnum.API:
            test_suite_detail.result_data = [i.model_dump() for i in data.result_data.steps]
            test_suite_detail.error_message = data.error_message
        else:
            test_suite_detail.result_data = data.result_data
            test_suite_detail.case_name = case_name
        test_suite_detail.status = data.status
        test_suite_detail.save()
        test_suite_detail_list = TestSuiteDetails.objects.filter(test_suite=data.test_suite,
                                                                 status__in=[TaskEnum.STAY_BEGIN.value,
                                                                             TaskEnum.PROCEED.value])

        if data.type == TestCaseTypeEnum.UI:
            TestReportWriting.update_test_case(data.result_data)
        if not test_suite_detail_list.exists():
            test_suite = TestSuiteDetails.objects.filter(test_suite=data.test_suite, status=StatusEnum.FAIL.value)
            if not test_suite.exists():
                cls.update_test_suite(data.test_suite, StatusEnum.SUCCESS.value)
            else:
                cls.update_test_suite(data.test_suite, StatusEnum.FAIL.value)
            cls.send_test_result(data.test_suite, data.error_message)

    @classmethod
    @orm_retry('send_test_result')
    def send_test_result(cls, test_suite_id: int, msg):
        connection.ensure_connection()
        test_suite = TestSuite.objects.get(id=test_suite_id)
        if test_suite.is_notice == StatusEnum.SUCCESS.value:
            NoticeMain.notice_main(test_suite.test_env, test_suite.project_product.id, test_suite_id)
        from src.auto_test.auto_system.consumers import ChatConsumer
        ChatConsumer.active_send(SocketDataModel(
            code=200 if test_suite.status else 300,
            msg=msg if msg else f'测试套ID：{test_suite_id} 执行完成',
            user=test_suite.user.username,
            is_notice=ClientTypeEnum.WEB,
        ))
