# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-12-11 16:16
# @Author : 毛鹏
import traceback
from datetime import datetime

import time
from mangotools.exceptions import MangoToolsError

from src.auto_test.auto_api.models import ApiCaseDetailed, ApiCase, ApiInfo, ApiCaseDetailedParameter
from src.auto_test.auto_api.service.base.api_base_test_setup import APIBaseTestSetup
from src.auto_test.auto_system.service.update_test_suite import UpdateTestSuite
from src.enums.api_enum import MethodEnum
from src.enums.tools_enum import StatusEnum, TaskEnum, TestCaseTypeEnum
from src.exceptions import *
from src.models.api_model import RequestModel, ApiCaseResultModel, ApiCaseStepsResultModel, ResponseModel
from src.models.system_model import TestSuiteDetailsResultModel
from src.tools.decorator.retry import async_task_db_connection
from ..base.case_base import CaseBase
from ..base.case_parameter import CaseParameter


class TestCase:

    def __init__(self,
                 user_id: int,
                 test_env: int,
                 case_id: int,
                 test_suite: int = None,
                 test_suite_details: int = None):
        self.user_id = user_id
        self.test_env = test_env
        self.case_id = case_id
        self.test_suite = test_suite
        self.test_suite_details = test_suite_details

        self.test_setup = APIBaseTestSetup()
        try:
            self.api_case: ApiCase = ApiCase.objects.get(id=case_id)
        except ApiCase.DoesNotExist:
            raise ApiError(*ERROR_MSG_0057)
        self.case_base = CaseBase(self.test_setup, self.api_case)

        self.api_case.status = TaskEnum.PROCEED.value
        self.api_case.save()
        self.api_case_result = ApiCaseResultModel(
            id=case_id,
            name=self.api_case.name,
            project_product_name=self.api_case.project_product.name,
            test_env=self.test_env,
            user_id=self.user_id,
            status=StatusEnum.FAIL.value,
            test_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def test_case(self, case_sort: int | None = None) -> ApiCaseResultModel:
        log.api.debug(f'开始执行用例ID：{self.case_id}')
        res = None
        try:
            self.test_setup.init_test_object(self.api_case.project_product_id, self.test_env)
            self.test_setup.init_public(self.api_case.project_product_id, self.test_env)
            self.case_base.case_front_main()
            if self.api_case.parametrize and isinstance(self.api_case.parametrize, list):
                for i in self.api_case.parametrize:
                    res: tuple[int, str] | None = self.case_detailed(self.case_id, case_sort, i)
            else:
                res: tuple[int, str] | None = self.case_detailed(self.case_id, case_sort)
            if res and isinstance(res, tuple):
                self.api_case_result.status, self.api_case_result.error_message = res[0], res[1]
            else:
                self.api_case_result.status, self.api_case_result.error_message = StatusEnum.SUCCESS.value, None
        except (MangoToolsError, MangoServerError) as e:
            self.update_test_case(self.case_id, TaskEnum.FAIL.value)
            traceback.print_exc()
            self.api_case_result.error_message = e.msg
        except Exception as error:
            self.update_test_case(self.case_id, TaskEnum.FAIL.value)
            traceback.print_exc()
            log.api.error(f'API用例执行过程中发生异常：{error}')
            self.api_case_result.error_message = f'API用例执行过程中发生异常：{error}'
        self.case_base.case_posterior_main()
        self.update_test_case(self.case_id, self.api_case_result.status)
        if self.test_suite and self.test_suite_details:
            UpdateTestSuite.update_test_suite_details(TestSuiteDetailsResultModel(
                id=self.test_suite_details,
                type=TestCaseTypeEnum.API,
                test_suite=self.test_suite,
                status=self.api_case_result.status,
                error_message=self.api_case_result.error_message,
                result_data=self.api_case_result
            ))
        log.api.debug(f'用例测试完成：{self.api_case_result.model_dump_json()}')
        return self.api_case_result

    def case_detailed(self,
                      case_id: int,
                      case_sort: int | None,
                      parametrize: dict | None = None
                      ) -> tuple[int, str] | None:
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
        self.case_base.case_parametrize(parametrize)
        for case_detailed in case_detailed_list:
            case_detailed.status = TaskEnum.PROCEED.value
            case_detailed.save()
            res: tuple[int, str] | None = self.detailed_parameter(case_detailed)
            if res:
                case_detailed.status = res[0]
                case_detailed.error_message = res[1] if len(res) > 1 else None
                case_detailed.save()
                return res
            else:
                case_detailed.status = StatusEnum.SUCCESS.value
                case_detailed.save()

    def detailed_parameter(self, case_detailed: ApiCaseDetailed) -> tuple[int, str] | None:
        res_list = []
        for parameter in ApiCaseDetailedParameter.objects.filter(case_detailed_id=case_detailed.id):
            case_parameter = CaseParameter(self.test_setup, parameter)
            self.test_setup.init_test_object(case_detailed.api_info.project_product_id, self.test_env)
            self.test_setup.init_public(case_detailed.api_info.project_product_id, self.test_env)
            error_retry = 0
            retry = parameter.error_retry + 1 if parameter.error_retry else 1
            status = StatusEnum.FAIL.value
            error_message = None
            log.api.debug(f'开始执行用例的场景：{parameter.name}，这个场景失败重试：{retry} 次')
            while error_retry < retry and status != StatusEnum.SUCCESS.value:
                error_retry += 1
                request_model = RequestModel(
                    method=MethodEnum(case_detailed.api_info.method).name,
                    url=case_detailed.api_info.url,
                    headers=case_parameter.headers(parameter, self.case_base.case_headers),
                    params=parameter.params,
                    data=parameter.data,
                    json=parameter.json,
                    file=parameter.file,
                    posterior_file=case_detailed.api_info.posterior_file,
                )
                res_model = ApiCaseStepsResultModel(
                    id=case_detailed.id,
                    api_info_id=case_detailed.api_info.id,
                    name=parameter.name,
                    status=StatusEnum.FAIL.value,
                    request=request_model,
                    cache_data={},
                    test_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )
                try:
                    request_model = case_parameter.front_main(request_model)
                    res_model.response = self.test_setup.api_request(
                        case_detailed.api_info_id, self.test_env, request_model)
                    res_model.response = case_parameter.posterior_main(res_model.response)
                    res_model.ass, status, error_message = case_parameter.ass_main(res_model.response)
                    res_model.status = status
                    res_model.error_message = error_message
                    res_model.cache_data = self.test_setup.test_data.get_all()
                    self.api_case_result.steps.append(res_model)
                    self.update_api_info(case_detailed.api_info.id, res_model.response, res_model.status)
                    self.update_test_case_detailed_parameter(parameter.id, res_model)
                    if parameter.retry_interval:
                        time.sleep(parameter.retry_interval)
                except (MangoServerError, MangoToolsError) as error:
                    res_model.cache_data = self.test_setup.test_data.get_all()
                    res_model.status = StatusEnum.FAIL.value
                    res_model.error_message = error.msg
                    if res_model.response:
                        self.update_api_info(case_detailed.api_info.id, res_model.response,
                                             res_model.status)
                    self.update_test_case_detailed_parameter(parameter.id, res_model)
                    return StatusEnum.FAIL.value, error.msg
                except Exception as error:
                    res_model.cache_data = self.test_setup.test_data.get_all()
                    res_model.status = StatusEnum.FAIL.value
                    if res_model.response:
                        self.update_api_info(case_detailed.api_info.id, res_model.response,
                                             res_model.status)
                    self.update_test_case_detailed_parameter(parameter.id, res_model)
                    log.api.error(f'API请求发生未知错误：{traceback.print_exc()}')
                    msg = f'发生未知错误，请联系管理员来处理异常，异常内容：{error}'
                    res_model.error_message = msg
                    return StatusEnum.FAIL.value, msg
            res_list.append({'status': status, 'error_message': error_message})
        for i in res_list:
            if i.get('status') == StatusEnum.FAIL.value:
                return i.get('status'), i.get('error_message')

    def update_api_info(self, _id: int, result_data: ResponseModel, status: int):
        model = ApiInfo.objects.get(id=_id)
        model.status = status
        result_data_dict = result_data.model_dump()
        result_data_dict['name'] = model.name
        result_data_dict['cache_all'] = self.test_setup.test_data.get_all()
        model.result_data = result_data_dict
        model.save()

    @classmethod
    @async_task_db_connection(max_retries=3, retry_delay=3)
    def update_test_case(cls, case_id: int, status: int):
        model = ApiCase.objects.get(id=case_id)
        model.status = status
        model.save()

    @classmethod
    @async_task_db_connection(max_retries=3, retry_delay=3)
    def update_test_case_detailed_parameter(cls, parameter_id, result_data: ApiCaseStepsResultModel):
        model = ApiCaseDetailedParameter.objects.get(id=parameter_id)
        model.status = result_data.status
        if result_data.request.file:
            result_data.request.file = str(result_data.request.file)
        model.result_data = result_data.model_dump()
        model.save()
