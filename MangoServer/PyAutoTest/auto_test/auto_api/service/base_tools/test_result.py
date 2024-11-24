# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-12-26 15:42
# @Author : 毛鹏
import json

from PyAutoTest.auto_test.auto_api.models import ApiCase, ApiInfo, ApiCaseDetailed
from PyAutoTest.auto_test.auto_system.views.test_suite import TestSuiteCRUD
from PyAutoTest.enums.system_enum import AutoTestTypeEnum
from PyAutoTest.enums.tools_enum import StatusEnum
from PyAutoTest.models.api_model import RequestDataModel, ResponseDataModel
from PyAutoTest.tools.view.snowflake import Snowflake


class TestResult:

    def __init__(self):
        self.test_suite_id = Snowflake.generate_id()
        self.project_product_id = None
        self.case_status = StatusEnum.FAIL.value
        self.case_error_message = None
        self.test_suite_data = None

    def result_init(self, project_product_id: int, case_id_list: list):
        self.project_product_id = project_product_id
        self.case_status = StatusEnum.FAIL.value
        self.case_error_message = None
        if self.test_suite_data is None:
            self.test_suite_data = TestSuiteCRUD.inside_post({
                'id': self.test_suite_id,
                'type': AutoTestTypeEnum.API.value,
                'project_product': self.project_product_id,
                'test_env': self.test_env,
                'error_message': None,
                'run_status': StatusEnum.FAIL.value,
                'status': None,
                'case_list': case_id_list,
                'is_notice': self.is_notice,
                'user': self.user_obj['id']
            })

    @staticmethod
    def json_none(data: dict | list | None):
        if data is None:
            return data
        return json.dumps(data, ensure_ascii=False)

    def add_api_info_result(self,
                            case_detailed: ApiCaseDetailed,
                            request_data_model: RequestDataModel | None = None,
                            response: ResponseDataModel | None = None,
                            ) -> None:
        data = {
            'test_suite_id': self.test_suite_id,
            'case_sort': case_detailed.case_sort,
            'case': case_detailed.case.id,
            'api_info': case_detailed.api_info.id,
            'case_detailed': case_detailed.id,
            'status': self.case_status,
            'all_cache': self.json_none(self.get_all())
        }
        if request_data_model:
            data['url'] = request_data_model.url
            data['headers'] = self.json_none(response.headers)
            data['params'] = self.json_none(request_data_model.params)
            data['data'] = self.json_none(request_data_model.data)
            data['json'] = self.json_none(request_data_model.json_data)
            data['file'] = str(request_data_model.file) if request_data_model.file else None
        if response:
            data['response_code'] = response.status_code
            data['response_time'] = str(response.response_time)
            data['response_headers'] = self.json_none(response.response_headers)
            data['response_text'] = response.response_text if response.response_text else None
            data['error_message'] = self.case_error_message
            data['assertion'] = self.json_none(self.ass_result)

        ApiInfoResultCRUD.inside_post(data)
        self.update_api_info(case_detailed.api_info.id, self.case_status)
        self.update_case_detailed(case_detailed.id, self.case_status)

    def add_api_case_result(self, case_id: int) -> None:
        ApiCaseResultCRUD.inside_post({
            'case': case_id,
            'test_suite_id': self.test_suite_id,
            'error_message': self.case_error_message,
            'status': self.case_status,
        })

    @classmethod
    def update_api_info(cls, api_info_id: int, status: int):
        api_info_obj = ApiInfo.objects.get(id=api_info_id)
        api_info_obj.status = status
        api_info_obj.save()

    def update_case(self, _id: int):
        api_case = ApiCase.objects.get(id=_id)
        api_case.test_suite_id = self.test_suite_id
        api_case.status = self.case_status
        api_case.save()

    @classmethod
    def update_case_detailed(cls, _id: int, status: int):
        api_info_obj = ApiCaseDetailed.objects.get(id=_id)
        api_info_obj.status = status
        api_info_obj.save()

    def update_test_suite(self, status: int, error_message: list):
        error_message = list(filter(None, error_message))
        test_suite_data = {
            'id': self.test_suite_id,
            'error_message': json.dumps(error_message, ensure_ascii=False) if error_message else None,
            'run_status': StatusEnum.SUCCESS.value,
            'status': status
        }
        TestSuiteCRUD.inside_put(self.test_suite_id, test_suite_data)
