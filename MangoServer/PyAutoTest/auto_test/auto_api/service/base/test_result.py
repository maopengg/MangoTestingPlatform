# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-12-26 15:42
# @Author : 毛鹏
import json

from PyAutoTest.auto_test.auto_api.models import ApiCase, ApiInfo, ApiCaseDetailed
from PyAutoTest.auto_test.auto_api.views.api_case_result import ApiCaseResultCRUD
from PyAutoTest.auto_test.auto_api.views.api_info_result import ApiInfoResultCRUD
from PyAutoTest.auto_test.auto_system.views.test_suite_report import TestSuiteReportCRUD
from PyAutoTest.enums.system_enum import AutoTestTypeEnum
from PyAutoTest.enums.tools_enum import StatusEnum
from PyAutoTest.models.apimodel import RequestDataModel, ResponseDataModel
from PyAutoTest.tools.view.snowflake import Snowflake


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

    def save_test_result(self,
                         case_detailed,
                         request_data_model: RequestDataModel | None = None,
                         response: ResponseDataModel | None = None,
                         ) -> None:
        if request_data_model and response:
            data = {
                'test_suite_id': self.test_suite_data['id'],
                'case_sort': case_detailed.case_sort,
                'case': case_detailed.case.id,
                'api_info': case_detailed.api_info.id,
                'case_detailed': case_detailed.id,

                'url': request_data_model.url,
                'headers': json.dumps(response.headers,
                                      ensure_ascii=False) if response.headers else None,
                'params': json.dumps(request_data_model.params,
                                     ensure_ascii=False) if request_data_model.params else None,
                'data': json.dumps(request_data_model.data,
                                   ensure_ascii=False) if request_data_model.data else None,
                'json': json.dumps(request_data_model.json_data,
                                   ensure_ascii=False) if request_data_model.json_data else None,
                'file': str(request_data_model.file) if request_data_model.file else None,

                'response_code': response.status_code,
                'response_time': str(response.response_time),
                'response_headers': json.dumps(response.response_headers, ensure_ascii=False),
                'response_text': response.response_text if response.response_text else None,
                # 'response_json': json.dumps(response.response_json,
                #                             ensure_ascii=False) if response.response_json else None,
                'status': self.assertion_result[-1],
                'error_message': self.error_message[-1] if self.error_message else None,
                'all_cache': json.dumps(self.get_all(), ensure_ascii=False) if self.get_all() else None,
            }
            ApiInfoResultCRUD().inside_post(data)
        self.update_api_info(case_detailed.api_info.id, self.assertion_result[-1])
        self.update_case_detailed(case_detailed.id, self.assertion_result[-1])

    def api_case_result_sava(self, case_id: int) -> None:
        data = {
            'case': case_id,
            'test_suite_id': self.test_suite_data['id'],
            'error_message': self.error_message[-1] if self.error_message else None,
            'status': self.assertion_result[-1],
        }
        ApiCaseResultCRUD().inside_post(data)

    def update_case_or_suite(self, case_id: int):
        api_case = ApiCase.objects.get(id=case_id)
        api_case.test_suite_id = self.test_suite_report.get('id')
        if StatusEnum.FAIL.value in self.assertion_result:
            self.update_test_suite(StatusEnum.FAIL.value)
            api_case.status = StatusEnum.FAIL.value
        else:
            self.update_test_suite(StatusEnum.SUCCESS.value)
            api_case.status = StatusEnum.SUCCESS.value
        api_case.save()

    @classmethod
    def update_api_info(cls, api_info_id: int, status: int):
        api_info_obj = ApiInfo.objects.get(id=api_info_id)
        api_info_obj.status = status
        api_info_obj.save()

    @classmethod
    def update_case_detailed(cls, _id: int, status: int):
        api_info_obj = ApiCaseDetailed.objects.get(id=_id)
        api_info_obj.status = status
        api_info_obj.save()

    def update_test_suite(self, status: int):
        test_suite_data = {
            'id': self.test_suite_data['id'],
            'error_message': json.dumps(self.error_message, ensure_ascii=False) if self.error_message else None,
            'run_status': StatusEnum.SUCCESS.value,
            'status': status
        }
        self.test_suite_report = TestSuiteReportCRUD().inside_put(self.test_suite_data['id'], test_suite_data)
