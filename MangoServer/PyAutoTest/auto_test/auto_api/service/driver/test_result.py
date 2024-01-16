# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-12-26 15:42
# @Author : 毛鹏
import json

from PyAutoTest.auto_test.auto_api.models import ApiCase, ApiInfo
from PyAutoTest.auto_test.auto_api.views.api_result import ApiResultCRUD
from PyAutoTest.auto_test.auto_system.views.test_suite_report import TestSuiteReportCRUD
from PyAutoTest.enums.system_enum import AutoTestTypeEnum
from PyAutoTest.enums.tools_enum import StatusEnum
from PyAutoTest.models.apimodel import RequestDataModel, ResponseDataModel
from PyAutoTest.tools.view_utils.snowflake import Snowflake


class TestResult:
    def __init__(self, project_id, test_obj_id):
        self.test_suite_data = {'id': Snowflake.generate_id(),
                                'type': AutoTestTypeEnum.API.value,
                                'project': project_id,
                                'test_object': test_obj_id,
                                'error_message': None,
                                'run_status': StatusEnum.FAIL.value}

        self.test_suite_report = TestSuiteReportCRUD().inside_post(self.test_suite_data)

        self.assertion_result = []
        self.error_message = []

    def save_test_result(self, case_detailed,
                         request_data_model: RequestDataModel | None = None,
                         response: ResponseDataModel | None = None,
                         ) -> None:
        """
        测试结果存储
        @param request_data_model:
        @param response:
        @param case_detailed:
        @return:
        """
        if request_data_model and response:
            data = {
                'case_detailed': case_detailed.id,
                'case': case_detailed.case.id,
                'api_info': case_detailed.api_info.id,
                'test_suite_id': self.test_suite_data['id'],
                'url': request_data_model.url,
                'method': request_data_model.method,
                'headers': json.dumps(response.headers, ensure_ascii=False),
                'params': json.dumps(request_data_model.params, ensure_ascii=False),
                'data': json.dumps(request_data_model.data, ensure_ascii=False),
                'json': json.dumps(request_data_model.json_data, ensure_ascii=False),
                'file': str(request_data_model.file),
                'response_code': response.status_code,
                'response_time': str(response.response_time),
                'response_headers': json.dumps(response.response_headers, ensure_ascii=False),
                'response_text': response.response_text,
                'response_json': json.dumps(response.response_json, ensure_ascii=False),
                'error_message': self.error_message[-1] if self.error_message else None,
                'status': self.assertion_result[-1],
                'all_cache': json.dumps(self.get_all(), ensure_ascii=False),
            }
            ApiResultCRUD().inside_post(data)
        self.update_api_info(case_detailed.api_info.id, self.assertion_result[-1])

    def update_case_or_suite(self, case_id: int):
        """
        更新用例状态和测试套
        @return:
        """
        api_case = ApiCase.objects.get(id=case_id)
        if StatusEnum.FAIL.value in self.assertion_result:
            self.update_test_suite(StatusEnum.FAIL.value)
            api_case.status = StatusEnum.FAIL.value
        else:
            self.update_test_suite(StatusEnum.FAIL.value)
            api_case.status = StatusEnum.SUCCESS.value
        api_case.save()

    @classmethod
    def update_api_info(cls, api_info_id: int, status: int):
        """
        修改api_info表的状态
        @param api_info_id: api_info_id
        @param status: status
        @return:
        """
        api_info_obj = ApiInfo.objects.get(id=api_info_id)
        api_info_obj.status = status
        api_info_obj.save()

    def update_test_suite(self, status: int):
        """
        更新测试套表
        @param status:
        @return:
        """
        test_suite_data = {
            'id': self.test_suite_data['id'],
            'error_message': json.dumps(self.error_message, ensure_ascii=False),
            'run_status': StatusEnum.SUCCESS.value,
            'status': status
        }
        self.test_suite_report = TestSuiteReportCRUD().inside_put(self.test_suite_data['id'], test_suite_data)
