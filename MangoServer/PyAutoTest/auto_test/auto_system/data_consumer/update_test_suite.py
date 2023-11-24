# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-10-25 17:24
# @Author : 毛鹏
import logging

from PyAutoTest.auto_test.auto_system.models import TestSuiteReport
from PyAutoTest.auto_test.auto_system.views.test_suite_report import TestSuiteReportSerializers
from PyAutoTest.models.socket_model.ui_model import TestSuiteModel, CaseResultModel

log = logging.getLogger('system')


class TestSuiteReportUpdate:

    def __init__(self, data: TestSuiteModel = None):
        self.data = data

    def update_test_suite_report(self):
        """
        新增一条测试套
        @return:
        """
        serializer = TestSuiteReportSerializers(data=self.data.dict())
        if serializer.is_valid():
            serializer.save()
            return serializer.data
        else:
            log.error(f'新增测试套报错，请联系管理员进行查看，错误信息：{serializer.errors}')

    @classmethod
    def update_case_suite(cls, data: CaseResultModel) -> None:
        pass
        # cls.update_case_suite_status(data.test_suite_id, data.test_result, self.data.run_status)
        # for i in data.case_res_list:
        #     ConsumerTestResult.update_case_status(i.case_id, i.test_result)
        #     ConsumerTestResult.update_case_result(i)

    @classmethod
    def update_case_suite_status(cls, _id, status, run_status=1, error_message=None):
        """
        @param _id:
        @param status:
        @param run_status:1是测试完成
        @param error_message:
        @return:
        """
        try:
            res = TestSuiteReport.objects.get(id=_id)
            res.status = status
            res.run_status = run_status
            if error_message:
                res.error_message = run_status
            res.save()
        except TestSuiteReport.DoesNotExist as e:
            # 处理找不到对应记录的情况
            log.error(f"当前查询结果是空，请检查id是否在数据库中存在id：{_id}报错：{e}")
