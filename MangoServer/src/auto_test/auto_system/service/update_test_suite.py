# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-25 15:04
# @Author : 毛鹏

from src.auto_test.auto_pytest.service.test_report_writing import PtestTestReportWriting
from src.auto_test.auto_system.models import TestSuite, TestSuiteDetails
from src.auto_test.auto_system.service.notice import NoticeMain
from src.auto_test.auto_system.service.testcounter import TestCounter
from src.auto_test.auto_ui.service.test_report_writing import TestReportWriting
from src.enums.system_enum import ClientTypeEnum
from src.enums.tools_enum import TaskEnum, StatusEnum, TestCaseTypeEnum
from src.models.socket_model import SocketDataModel
from src.models.system_model import TestSuiteDetailsResultModel
from src.tools.log_collector import log


class UpdateTestSuite:

    @classmethod
    def update_test_suite(cls, test_suite_id: int, status: int):
        test_suite = TestSuite.objects.get(id=test_suite_id)
        test_suite.status = status
        test_suite.save()

    @classmethod
    def update_test_suite_details(cls, data: TestSuiteDetailsResultModel):
        log.system.debug(f'开始更新测试套数据：{data.model_dump_json()}')
        test_suite_detail = TestSuiteDetails.objects.get(id=data.id)
        test_suite_detail.status = data.status
        if data.type == TestCaseTypeEnum.UI:
            test_suite_detail.result_data = [i.model_dump() for i in data.result_data.steps]
            test_suite_detail.error_message = data.error_message
            TestReportWriting.update_test_case(data.result_data)
        elif data.type == TestCaseTypeEnum.API:
            test_suite_detail.result_data = [i.model_dump() for i in data.result_data.steps]
            test_suite_detail.error_message = data.error_message
        else:
            test_suite_detail.result_data = data.result_data.result_data
            test_suite_detail.case_name = data.result_data.name
            PtestTestReportWriting.update_pytest_test_case(data.result_data)
        test_suite_detail.save()
        TestCounter.res_main(test_suite_detail.id)
        test_suite_detail_list = TestSuiteDetails.objects.filter(
            test_suite=data.test_suite,
            status__in=[TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value]
        )
        if not test_suite_detail_list.exists():
            test_suite = TestSuiteDetails.objects.filter(test_suite=data.test_suite, status=StatusEnum.FAIL.value)
            if not test_suite.exists():
                cls.update_test_suite(data.test_suite, StatusEnum.SUCCESS.value)
            else:
                cls.update_test_suite(data.test_suite, StatusEnum.FAIL.value)
            cls.send_test_result(data.test_suite, data.error_message)

    @classmethod
    def send_test_result(cls, test_suite_id: int, msg: str):
        test_suite = TestSuite.objects.get(id=test_suite_id)
        if test_suite.is_notice != StatusEnum.SUCCESS.value and test_suite.tasks is not None and test_suite.tasks.notice_group and test_suite.tasks.is_notice == StatusEnum.SUCCESS.value:
            if (test_suite.tasks.fail_notice == StatusEnum.SUCCESS.value and test_suite.status != StatusEnum.SUCCESS.value) or test_suite.tasks.fail_notice!= StatusEnum.SUCCESS.value:
                NoticeMain.notice_main(test_suite.tasks.notice_group_id, test_suite_id)

        test_suite.is_notice = StatusEnum.SUCCESS.value
        test_suite.save()
        from src.auto_test.auto_system.consumers import ChatConsumer
        ChatConsumer.active_send(SocketDataModel(
            code=200 if test_suite.status else 300,
            msg=f'测试套ID：{test_suite_id} 执行完成，结果：{msg}' if msg else f'测试套ID：{test_suite_id} 执行完成',
            user=test_suite.user.username,
            is_notice=ClientTypeEnum.WEB,
        ))
