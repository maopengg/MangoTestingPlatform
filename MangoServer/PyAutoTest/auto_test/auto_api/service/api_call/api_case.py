# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-12-11 16:16
# @Author : 毛鹏
from typing import Optional
from urllib.parse import urljoin

from PyAutoTest.auto_test.auto_api.models import ApiCaseDetailed, ApiCase
from PyAutoTest.auto_test.auto_api.service.base_tools.dependence import CaseMethod
from PyAutoTest.auto_test.auto_api.service.base_tools.test_result import TestResult
from PyAutoTest.auto_test.auto_system.consumers import ChatConsumer
from PyAutoTest.auto_test.auto_system.service.notic_tools import NoticeMain
from PyAutoTest.auto_test.auto_user.models import TestObject
from PyAutoTest.auto_test.auto_user.tools.factory import func_test_object_value
from PyAutoTest.enums.api_enum import MethodEnum
from PyAutoTest.enums.tools_enum import StatusEnum, ClientTypeEnum, AutoTypeEnum
from PyAutoTest.exceptions import MangoServerError
from PyAutoTest.exceptions.api_exception import CaseIsEmptyError, UnknownError
from PyAutoTest.exceptions.error_msg import *
from PyAutoTest.exceptions.tools_exception import SyntaxErrorError, MysqlQueryIsNullError
from PyAutoTest.models.apimodel import RequestDataModel, ResponseDataModel
from PyAutoTest.models.socket_model import SocketDataModel


class ApiCaseRun(CaseMethod, TestResult):

    def __init__(self, test_env: int, case_sort: int = None, is_notice: int = 0, user_obj: dict = None):
        CaseMethod.__init__(self)
        TestResult.__init__(self)
        self.test_env = test_env
        self.user_obj = user_obj
        self.case_sort = case_sort
        self.is_notice = is_notice

        self.test_object: Optional[TestObject | None] = None
        self.headers = None

    def case_batch(self, case_list: list):
        case_status_list = []
        case_error_message_list = []
        api_case_obj = ApiCase.objects.get(id=case_list[0])
        self.result_init(api_case_obj.project_product_id, case_list)
        for case_id in case_list:
            try:
                self.case(case_id)
                case_status_list.append(self.case_status)
                case_error_message_list.append(self.case_error_message)
            except (UnknownError, CaseIsEmptyError):
                pass
        if StatusEnum.FAIL.value in case_status_list:
            self.update_test_suite(StatusEnum.FAIL.value, case_error_message_list)
        else:
            self.update_test_suite(StatusEnum.SUCCESS.value, case_error_message_list)
        if self.is_notice:
            NoticeMain.notice_main(self.project_product_id, self.test_suite_id)

    def case(self, case_id: int, is_case_one: bool = False) -> dict:
        api_case: ApiCase = self.__case_init(case_id, is_case_one)
        try:
            for api_info in self.__case_api_detailed(case_id):
                if not self.case_step_api(api_info):
                    break
            self.__case_last(api_case)
        except UnknownError as error:
            self.add_api_case_result(case_id)
            self.update_test_suite(self.case_status, [error.msg])
            raise error
        return {
            'test_suite': self.test_suite_id,
            'status': self.case_status,
            'error_message': self.case_error_message
        }

    def case_step_api(self, case_detailed: ApiCaseDetailed) -> bool:
        try:
            self.__case_step_init(case_detailed)
            request_data_model = RequestDataModel(method=MethodEnum(case_detailed.api_info.method).name,
                                                  url=urljoin(self.test_object.value, case_detailed.url),
                                                  headers=case_detailed.header,
                                                  params=case_detailed.params,
                                                  data=case_detailed.data,
                                                  json_data=case_detailed.json,
                                                  file=case_detailed.file)
            response: ResponseDataModel = self.send_request(request_data_model)
            return self.__case_step_last(case_detailed, request_data_model, response)
        except MangoServerError as error:
            self.case_status = StatusEnum.FAIL.value
            self.case_error_message = error.msg
            self.add_api_info_result(case_detailed)
            return False
        # except Exception as error:
        #     log.api.error(
        #         f'执行接口请求时发生未知异常，请联系管理员！用例ID：{case_detailed.case_id}，错误类型：{type(error)}，错误详情：{error}')
        #     self.case_status = StatusEnum.FAIL.value
        #     self.case_error_message = ERROR_MSG_0040[1]
        #     self.add_api_info_result(case_detailed)
        #     raise False

    def __case_api_detailed(self, case_id: int) -> list[ApiCaseDetailed]:
        if self.case_sort:
            case_api_list = ApiCaseDetailed.objects.filter(case=case_id,
                                                           case_sort__lte=self.case_sort).order_by('case_sort')
        else:
            case_api_list = ApiCaseDetailed.objects.filter(case=case_id).order_by('case_sort')
        if not case_api_list:
            raise CaseIsEmptyError(*ERROR_MSG_0008)
        return case_api_list

    def __case_init(self, case_id: int, is_case_one: bool):
        api_case = ApiCase.objects.get(id=case_id)
        if is_case_one:
            self.result_init(api_case.project_product_id, [case_id])

        #  有大问题，多个产品之前不能组合成一个用例！！！
        self.test_object = func_test_object_value(self.test_env,
                                                  api_case.project_product_id,
                                                  AutoTypeEnum.API.value)
        self.common_init(self.test_object, api_case.project_product_id)
        # ↑

        for custom in api_case.front_custom:
            self.set_cache(custom.get('key'), custom.get('value'))
        for i in api_case.front_sql:
            if self.mysql_connect:
                sql = self.replace(i.get('sql'))
                result_list: list[dict] = self.mysql_connect.condition_execute(sql)
                if isinstance(result_list, list):
                    for result in result_list:
                        try:
                            key_list = eval(i.get('key_list'))
                            for value, key in zip(result, key_list):
                                self.set_cache(key, result.get(value))
                        except SyntaxError:
                            raise SyntaxErrorError(*ERROR_MSG_0036)
                        except NameError:
                            raise SyntaxErrorError(*ERROR_MSG_0036)
                    if not result_list:
                        raise MysqlQueryIsNullError(*ERROR_MSG_0034, value=(sql,))
        if api_case.front_headers:
            self.headers = api_case.front_headers

        return api_case

    def __case_last(self, api_case: ApiCase):
        self.add_api_case_result(api_case.id)
        self.update_case(api_case.id)
        self.update_test_suite(self.case_status, [self.case_error_message])
        ChatConsumer.active_send(SocketDataModel(
            code=200 if self.case_status == StatusEnum.SUCCESS.value else 300,
            msg=f'用例：{api_case.name}，测试结果：{self.case_error_message}' if self.case_error_message else f'用例：{api_case.name}测试成功',
            user=self.user_obj['username'],
            is_notice=ClientTypeEnum.WEB.value, ))
        if self.mysql_connect:
            for sql in api_case.posterior_sql:
                self.mysql_connect.condition_execute(self.replace(sql.get('sql')))

    def __case_step_init(self, case_detailed: ApiCaseDetailed):
        self.front_sql(case_detailed)

    def __case_step_last(self,
                         case_detailed: ApiCaseDetailed,
                         request_data_model: RequestDataModel,
                         response: ResponseDataModel) -> bool:
        try:
            # 断言
            self.assertion(response, case_detailed)
            # 后置处理
            self.posterior(response, case_detailed)
        except MangoServerError as error:
            self.case_status = StatusEnum.FAIL.value
            self.case_error_message = error.msg
            self.add_api_info_result(case_detailed, request_data_model, response)
            return False
        # except Exception as error:
        #     log.api.error(
        #         f'执行接口断言时发生未知异常，请联系管理员！用例ID：{case_detailed.case_id}，错误类型：{type(error)}，错误详情：{error}')
        #     self.case_status = StatusEnum.FAIL.value
        #     self.case_error_message = ERROR_MSG_0040[1]
        #     self.add_api_info_result(case_detailed, request_data_model, response)
        #     raise UnknownError(*ERROR_MSG_0040)
        self.case_status = StatusEnum.SUCCESS.value
        self.add_api_info_result(case_detailed, request_data_model, response)
        return True
