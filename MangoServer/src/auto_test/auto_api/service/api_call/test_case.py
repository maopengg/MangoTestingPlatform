# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-12-11 16:16
# @Author : 毛鹏
import traceback
from copy import deepcopy
from typing import Optional
from urllib.parse import urljoin

from src.auto_test.auto_api.models import ApiCaseDetailed, ApiCase, ApiInfo, ApiHeaders, ApiCaseDetailedParameter
from src.auto_test.auto_api.service.base_tools.case_detailed import CaseDetailedInit
from src.auto_test.auto_system.service.update_test_suite import UpdateTestSuite
from src.enums.api_enum import MethodEnum
from src.enums.tools_enum import StatusEnum, TaskEnum, AutoTestTypeEnum
from src.exceptions import *
from src.models.api_model import RequestDataModel, ApiCaseResultModel, ApiCaseStepsResultModel
from src.models.system_model import TestSuiteDetailsResultModel


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

        self.case_headers = {}

        self.api_case_result: Optional[ApiCaseResultModel | None] = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def test_case(self, case_id: int, case_sort: int | None = None) -> ApiCaseResultModel:
        log.api.debug(f'开始执行用例ID：{case_id}')
        api_case = ApiCase.objects.get(id=case_id)
        api_case.status = TaskEnum.PROCEED.value
        api_case.save()
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
            self.update_test_case(case_id)
            if self.test_suite:
                UpdateTestSuite.update_test_suite_details(TestSuiteDetailsResultModel(
                    id=self.test_suite_details,
                    type=AutoTestTypeEnum.API,
                    test_suite=self.test_suite,
                    status=self.status.value,
                    error_message=self.error_message,
                    result_data=self.api_case_result
                ))
            api_case.status = self.status.value
            api_case.save()
            return self.api_case_result
        except Exception as error:
            api_case.status = TaskEnum.FAIL.value
            api_case.save()
            traceback.print_exc()
            log.api.error(f'API用例执行过程中发生异常：{error}')
            self.api_case_result.error_message = f'API用例执行过程中发生异常：{error}'
            return self.api_case_result

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
            for case_detailed in case_detailed_list:
                for case_detailed_parameter in ApiCaseDetailedParameter.objects.filter(
                        case_detailed_id=case_detailed.id):
                    request_data_model = self.case_steps_front(case_detailed, case_detailed_parameter)
                    request_data_model, response = self.send_request(request_data_model)
                    self.posterior(response, case_detailed_parameter)
                    api_case_steps_result = ApiCaseStepsResultModel(
                        id=case_detailed.id,
                        api_info_id=case_detailed.api_info.id,
                        name=case_detailed_parameter.name,
                        status=self.status.value,
                        error_message=self.error_message,
                        ass=self.assertion(response, case_detailed_parameter),
                        request=request_data_model,
                        response=response,
                        cache_data=self.get_all()
                    )
                    self.api_case_result.steps.append(api_case_steps_result)

                    self.update_case_detailed_parameter(case_detailed_parameter.id, api_case_steps_result)
                    if self.status == StatusEnum.FAIL:
                        break
                self.update_api_info(case_detailed.api_info.id)
                self.update_case_detailed(case_detailed.id)
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

    def case_steps_front(self,
                         case_detailed: ApiCaseDetailed,
                         case_detailed_parameter: ApiCaseDetailedParameter) -> RequestDataModel:
        case_detailed.status = TaskEnum.PROCEED.value
        case_detailed.save()
        self.project_product_id = case_detailed.api_info.project_product.id
        self.init_test_object()
        self.front_sql(case_detailed_parameter)
        request_data_model = self.request_data_clean(RequestDataModel(
            method=MethodEnum(case_detailed.api_info.method).name,
            url=urljoin(self.test_object.value, case_detailed.api_info.url),
            headers=self.headers(case_detailed_parameter),
            params=case_detailed_parameter.params,
            data=case_detailed_parameter.data,
            json_data=case_detailed_parameter.json,
            file=case_detailed_parameter.file
        ))
        return request_data_model

    def update_api_info(self, api_info_id: int):
        model = ApiInfo.objects.get(id=api_info_id)
        model.status = self.status.value
        model.save()

    def update_test_case(self, case_id: int, ):
        model = ApiCase.objects.get(id=case_id)
        model.status = self.status.value
        model.save()

    def update_case_detailed(self, case_detailed_id: int):
        model = ApiCaseDetailed.objects.get(id=case_detailed_id)
        model.status = self.status.value
        model.save()

    def update_case_detailed_parameter(self, case_detailed_parameter_id, result_data: ApiCaseStepsResultModel):
        model = ApiCaseDetailedParameter.objects.get(id=case_detailed_parameter_id)
        model.status = self.status.value
        model.result_data = result_data.model_dump()
        model.save()

    def headers(self, case_detailed_parameter: ApiCaseDetailedParameter) -> dict:
        if case_detailed_parameter.header:
            case_details_header = {}
            for i in ApiHeaders.objects.filter(id__in=case_detailed_parameter.header):
                case_details_header[i.key] = i.value
            case_headers = deepcopy(self.case_headers)
            case_headers.update(case_details_header)
            return case_headers
        return self.case_headers
