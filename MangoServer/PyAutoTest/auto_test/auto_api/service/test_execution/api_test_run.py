# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-12-11 16:16
# @Author : 毛鹏
import logging
from urllib.parse import urljoin

from PyAutoTest.auto_test.auto_api.models import ApiCaseDetailed, ApiCase
from PyAutoTest.auto_test.auto_api.service.base.dependence import ApiDataHandle
from PyAutoTest.auto_test.auto_api.service.base.test_result import TestResult
from PyAutoTest.auto_test.auto_system.consumers import ChatConsumer
from PyAutoTest.auto_test.auto_system.service.notic_tools import NoticeMain
from PyAutoTest.enums.api_enum import MethodEnum
from PyAutoTest.enums.tools_enum import StatusEnum, ClientTypeEnum
from PyAutoTest.exceptions import MangoServerError
from PyAutoTest.exceptions.api_exception import CaseIsEmptyError, UnknownError
from PyAutoTest.exceptions.tools_exception import SyntaxErrorError, MysqlQueryIsNullError
from PyAutoTest.models.apimodel import RequestDataModel, ResponseDataModel
from PyAutoTest.models.socket_model import SocketDataModel
from PyAutoTest.tools.view.error_msg import *

log = logging.getLogger('api')


class ApiTestRun(ApiDataHandle, TestResult):

    def __init__(self, test_obj_id: int, case_sort: int = None, is_notice: int = 0, user_obj: dict = None):
        ApiDataHandle.__init__(self, test_obj_id)
        TestResult.__init__(self, test_obj_id)
        self.user_obj = user_obj
        self.case_sort = case_sort
        self.is_notice = is_notice
        self.is_batch = False

    def run_one_case(self, case_id: int, case_list: list = None) -> dict:
        api_case_obj = ApiCase.objects.get(id=case_id)
        self.common_init(api_case_obj.project_id)
        self.result_init(api_case_obj.project_id, case_list if case_list else [case_id])
        self.__case_front(api_case_obj)
        try:
            case_api_list = self.get_case(case_id)
            for api_info in case_api_list:
                if not self.run_api(api_info):
                    break
            self.add_api_case_result(case_id)
            self.update_case(case_id)
            if not self.is_batch:
                self.update_test_suite(self.case_status, [self.case_error_message])
            else:
                ChatConsumer.active_send(SocketDataModel(
                    code=200 if self.case_status == StatusEnum.SUCCESS.value else 300,
                    msg=f'用例：{api_case_obj.name}，测试结果：{self.case_error_message}' if self.case_error_message else f'用例：{api_case_obj.name}测试成功',
                    user=self.user_obj['username'],
                    is_notice=ClientTypeEnum.WEB.value, ))
            self.__case_posterior(api_case_obj)
        except UnknownError as error:
            self.add_api_case_result(case_id)
            if not self.is_batch:
                self.update_test_suite(self.case_status, [error.msg])
            raise error
        return {
            'test_suite': self.test_suite_id,
            'status': self.case_status,
            'error_message': self.case_error_message
        }

    def case_batch(self, case_list: list):
        self.is_batch = True

        case_status_list = []
        case_error_message_list = []
        for case_id in case_list:
            try:
                self.run_one_case(case_id, case_list)
                case_status_list.append(self.case_status)
                case_error_message_list.append(self.case_error_message)
            except UnknownError:
                pass
        if StatusEnum.FAIL.value in case_status_list:
            self.update_test_suite(StatusEnum.FAIL.value, case_error_message_list)
        else:
            self.update_test_suite(StatusEnum.SUCCESS.value, case_error_message_list)
        if self.is_notice:
            NoticeMain.notice_main(self.project_id, self.test_suite_id)

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
            response: ResponseDataModel = self.http(request_data_model)
        except MangoServerError as error:
            self.case_status = StatusEnum.FAIL.value
            self.case_error_message = error.msg
            self.add_api_info_result(case_detailed)
            return False
        except Exception as error:
            log.info(f'执行接口请求时发生未知异常，请联系管理员！用例ID：{case_detailed.case_id}，错误类型：{type(error)}，错误详情：{error}')
            self.case_status = StatusEnum.FAIL.value

            self.case_error_message = ERROR_MSG_0040[1]
            self.add_api_info_result(case_detailed)
            raise UnknownError(*ERROR_MSG_0040)
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
        except Exception as error:
            log.info(f'执行接口断言时发生未知异常，请联系管理员！用例ID：{case_detailed.case_id}，错误类型：{type(error)}，错误详情：{error}')
            self.case_status = StatusEnum.FAIL.value
            self.case_error_message = ERROR_MSG_0040[1]
            self.add_api_info_result(case_detailed, request_data_model, response)
            raise UnknownError(*ERROR_MSG_0040)
        self.case_status = StatusEnum.SUCCESS.value
        self.add_api_info_result(case_detailed, request_data_model, response)
        return True

    def get_case(self, case_id: int):
        if self.case_sort:
            case_api_list = ApiCaseDetailed.objects.filter(case=case_id, case_sort__lte=self.case_sort).order_by(
                'case_sort')
        else:
            case_api_list = ApiCaseDetailed.objects.filter(case=case_id).order_by('case_sort')
        if not case_api_list:
            raise CaseIsEmptyError(*ERROR_MSG_0008)
        return case_api_list

    def __case_front(self, api_case_obj: ApiCase):
        for custom in api_case_obj.front_custom:
            self.set_cache(custom.get('key'), custom.get('value'))
        for i in api_case_obj.front_sql:
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

    def __case_posterior(self, api_case_obj: ApiCase):
        if self.mysql_connect:
            for sql in api_case_obj.posterior_sql:
                self.mysql_connect.condition_execute(self.replace(sql.get('sql')))
