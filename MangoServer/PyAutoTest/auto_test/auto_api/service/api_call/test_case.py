# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-12-11 16:16
# @Author : 毛鹏
import traceback
from typing import Optional
from urllib.parse import urljoin

from PyAutoTest.auto_test.auto_api.models import ApiCaseDetailed, ApiCase, ApiInfo
from PyAutoTest.auto_test.auto_api.service.base_tools.case_detailed import CaseDetailedInit
from PyAutoTest.auto_test.auto_system.service.update_test_suite import UpdateTestSuite
from PyAutoTest.enums.api_enum import MethodEnum
from PyAutoTest.enums.tools_enum import StatusEnum
from PyAutoTest.exceptions import *
from PyAutoTest.models.api_model import RequestDataModel, ApiCaseResultModel, ResponseDataModel, ApiCaseStepsResultModel
from PyAutoTest.models.system_model import TestSuiteDetailsResultModel


class TestCase(CaseDetailedInit):

    def __init__(self,
                 user_id: int,
                 test_env: int,
                 tasks_id: int = None,
                 test_suite: int = None,
                 test_suite_details: int = None,
                 is_send: bool = False):
        super().__init__(user_id, test_env, tasks_id, is_send)
        self.test_suite = test_suite
        self.test_suite_details = test_suite_details

        self.headers = {}

        self.api_case_result: Optional[ApiCaseResultModel | None] = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def test_case(self, case_id: int, case_sort: int | None = None) -> ApiCaseResultModel:
        log.api.debug(f'开始执行用例ID：{case_id}')
        api_case = ApiCase.objects.get(id=case_id)
        self.api_case_result = ApiCaseResultModel(
            id=case_id,
            name=api_case.name,
            test_env=self.test_env,
            user_id=self.user_id,
            status=StatusEnum.FAIL.value,
            error_message=self.error_message,
        )
        try:
            self.project_product_id = api_case.project_product.id
            self.init_public()
            self.init_case_front(api_case)

            self.case_detailed(case_id, case_sort)

            self.init_case_posterior(api_case)
            self.api_case_result.status = self.status.value
            self.api_case_result.error_message = self.error_message
            self.update_test_case(case_id, self.status)
            if self.test_suite:
                UpdateTestSuite.update_test_suite_details(TestSuiteDetailsResultModel(
                    id=self.test_suite_details,
                    test_suite=self.test_suite,
                    status=self.status.value,
                    error_message=self.error_message,
                    result_data=self.api_case_result
                ))
            return self.api_case_result
        except Exception as error:
            traceback.print_exc()
            log.api.error(f'API用例执行过程中发生异常：{error}')

    def case_detailed(self, case_id: int, case_sort: int | None):
        if case_sort:
            case_detailed_list = ApiCaseDetailed \
                .objects \
                .filter(case=case_id, case_sort__lte=case_sort) \
                .order_by('case_sort')
        else:
            case_detailed_list = ApiCaseDetailed \
                .objects \
                .filter(case=case_id) \
                .order_by('case_sort')
        if not case_detailed_list:
            raise ApiError(*ERROR_MSG_0008)
        # 这里有问题
        try:
            for i in case_detailed_list:
                request_data_model = self.case_steps_front(i)

                request_data_model, response = self.send_request(request_data_model)
                self.case_steps_posterior(i, request_data_model, response)
                if self.status == StatusEnum.FAIL:
                    break
        except MangoServerError as error:
            self.status = StatusEnum.FAIL
            self.error_message = error.msg
        except Exception as error:
            traceback.print_exc()
            self.status = StatusEnum.FAIL
            log.api.error(error)
            self.error_message = f'发生未知错误，请联系管理员来处理异常，异常内容：{error}'

    def case_steps_front(self, data: ApiCaseDetailed) -> RequestDataModel:
        self.project_product_id = data.api_info.project_product.id
        self.init_test_object()
        self.front_sql(data)
        request_data_model = self.request_data_clean(RequestDataModel(
            method=MethodEnum(data.api_info.method).name,
            url=urljoin(self.test_object.value, data.url),
            headers=data.header,
            params=data.params,
            data=data.data,
            json_data=data.json,
            file=data.file
        ))
        return request_data_model

    def case_steps_posterior(
            self,
            data: ApiCaseDetailed,
            request: RequestDataModel,
            response: ResponseDataModel):
        ass = self.assertion(response, data)
        self.posterior(response, data)
        api_case_steps_result = ApiCaseStepsResultModel(
            id=data.api_info.id,
            name=data.api_info.name,
            status=self.status.value,
            error_message=self.error_message,
            ass=ass,
            request=request,
            response=response,
            cache_data=self.get_all()
        )
        self.api_case_result.steps.append(api_case_steps_result)
        self.update_api_info(data.api_info.id, self.status)
        self.update_case_detailed(data.id, self.status, api_case_steps_result)

    @classmethod
    def update_api_info(cls, api_info_id: int, status: StatusEnum):
        api_info_obj = ApiInfo.objects.get(id=api_info_id)
        api_info_obj.status = status.value
        api_info_obj.save()

    @classmethod
    def update_test_case(cls, case_id: int, status: StatusEnum):
        api_case = ApiCase.objects.get(id=case_id)
        api_case.status = status.value
        api_case.save()

    @classmethod
    def update_case_detailed(cls, case_detailed_id: int, status: StatusEnum, result_data: ApiCaseStepsResultModel):
        api_info_obj = ApiCaseDetailed.objects.get(id=case_detailed_id)
        api_info_obj.status = status.value
        api_info_obj.result_data = result_data.model_dump()
        api_info_obj.save()
