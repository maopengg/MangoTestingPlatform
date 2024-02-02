# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-12-11 16:16
# @Author : 毛鹏
from urllib.parse import urljoin

from PyAutoTest.auto_test.auto_api.models import ApiCaseDetailed
from PyAutoTest.auto_test.auto_api.service.base.dependence import ApiDataHandle
from PyAutoTest.auto_test.auto_api.service.base.http_request import HTTPRequest
from PyAutoTest.auto_test.auto_api.service.base.test_result import TestResult
from PyAutoTest.auto_test.auto_system.service.notic_tools import NoticeMain
from PyAutoTest.enums.api_enum import MethodEnum
from PyAutoTest.enums.tools_enum import StatusEnum
from PyAutoTest.exceptions import MangoServerError
from PyAutoTest.exceptions.api_exception import CaseIsEmptyError
from PyAutoTest.models.apimodel import RequestDataModel, ResponseDataModel
from PyAutoTest.tools.view_utils.error_msg import ERROR_MSG_0008


class ApiTestRun(ApiDataHandle, TestResult):

    def __init__(self, project_id: int, test_obj_id: int, case_sort: int = None, is_notice: bool = False):
        ApiDataHandle.__init__(self, project_id, test_obj_id)
        TestResult.__init__(self, project_id, test_obj_id)
        self.case_sort = case_sort
        self.is_notice = is_notice

    def run_one_case(self, case_id: int) -> dict:
        """
        执行一个用例
        @return:
        """
        case_list = self.get_case(case_id)
        if not case_list:
            raise CaseIsEmptyError(*ERROR_MSG_0008)
        for api_info in case_list:
            if not self.run_api(api_info):
                break
        self.api_case_result_sava(case_id)
        self.update_case_or_suite(case_id)
        return {
            'test_suite': self.test_suite_data['id'],
            'ass_result': self.assertion_result,
            'error_message': self.error_message
        }

    def case_batch(self, case_list: list):
        for case_id in case_list:
            self.run_one_case(case_id)
        if self.is_notice:
            NoticeMain.notice_main(self.project_id, self.test_suite_data['id'])

    def run_api(self, case_detailed: ApiCaseDetailed) -> bool:
        try:
            self.front_sql(case_detailed)
            request_data_model = self.request_data(
                RequestDataModel(method=MethodEnum(case_detailed.api_info.method).name,
                                 url=urljoin(self.test_object.value, case_detailed.url),
                                 headers=case_detailed.header,
                                 params=case_detailed.params,
                                 data=case_detailed.data,
                                 json_data=case_detailed.json,
                                 file=case_detailed.file))
            response: ResponseDataModel = HTTPRequest.http(request_data_model)
        except MangoServerError as error:
            self.assertion_result.append(StatusEnum.FAIL.value)
            self.error_message.append(f'接口：{case_detailed.api_info.name}{error.msg}')
            self.save_test_result(case_detailed)
            return False
        try:
            # 断言
            self.assertion(response, case_detailed)
            # 后置处理
            self.posterior(response, case_detailed)
            # 数据清除
            self.dump_data(case_detailed)
        except MangoServerError as error:
            self.error_message.append(f'接口：{case_detailed.api_info.name}{error.msg}')
            self.assertion_result.append(StatusEnum.FAIL.value)
            self.save_test_result(case_detailed, request_data_model, response)
            return False
        self.assertion_result.append(StatusEnum.SUCCESS.value)
        self.save_test_result(case_detailed, request_data_model, response)
        return True

    def get_case(self, case_id: int):
        if self.case_sort:
            return ApiCaseDetailed.objects.filter(case=case_id, case_sort__lte=self.case_sort).order_by('case_sort')
        else:
            return ApiCaseDetailed.objects.filter(case=case_id).order_by('case_sort')