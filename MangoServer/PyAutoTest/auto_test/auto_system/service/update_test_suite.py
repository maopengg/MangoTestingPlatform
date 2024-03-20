# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-10-25 17:24
# @Author : 毛鹏
import logging

from PyAutoTest.auto_test.auto_system.models import TestSuiteReport
from PyAutoTest.auto_test.auto_system.service.notic_tools import NoticeMain
from PyAutoTest.auto_test.auto_system.views.test_suite_report import TestSuiteReportSerializers
from PyAutoTest.models.socket_model.ui_model import TestSuiteModel
from PyAutoTest.tools.decorator.retry import retry

log = logging.getLogger('system')


class TestSuiteReportUpdate:

    def __init__(self, data: TestSuiteModel = None):
        self.data = data

    def add_test_suite_report(self):
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
    @retry(func_name='update_case_suite_status')
    def update_case_suite_status(cls, data: TestSuiteModel):
        """
        更新测试套
        @param data:
        @return:
        """
        res = TestSuiteReport.objects.get(id=data.id)
        res.status = data.status
        res.run_status = data.run_status
        if data.error_message:
            res.error_message = data.error_message
        res.save()
        if data.is_notice:
            NoticeMain.notice_main(data.project, data.id)
