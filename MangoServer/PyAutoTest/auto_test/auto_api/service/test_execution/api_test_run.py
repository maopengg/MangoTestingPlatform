# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-12-11 16:16
# @Author : 毛鹏
from urllib.parse import urljoin

from PyAutoTest.auto_test.auto_api.models import ApiCaseDetailed, ApiCase
from PyAutoTest.auto_test.auto_api.service.base.dependence import ApiDataHandle
from PyAutoTest.auto_test.auto_api.service.base.test_result import TestResult
from PyAutoTest.auto_test.auto_system.consumers import ChatConsumer
from PyAutoTest.auto_test.auto_system.service.notic_tools import NoticeMain
from PyAutoTest.enums.api_enum import MethodEnum
from PyAutoTest.enums.tools_enum import StatusEnum, ClientTypeEnum
from PyAutoTest.exceptions import MangoServerError
from PyAutoTest.exceptions.api_exception import CaseIsEmptyError
from PyAutoTest.exceptions.tools_exception import SyntaxErrorError, MysqlQueryIsNullError
from PyAutoTest.models.apimodel import RequestDataModel, ResponseDataModel
from PyAutoTest.models.socket_model import SocketDataModel
from PyAutoTest.tools.view.error_msg import *


class ApiTestRun(ApiDataHandle, TestResult):

    def __init__(self, test_obj_id: int, case_sort: int = None, is_notice: int = 0, username: str = None):
        ApiDataHandle.__init__(self, test_obj_id)
        TestResult.__init__(self, test_obj_id)
        self.username = username
        self.case_sort = case_sort
        self.is_notice = bool(is_notice)
        self.is_batch = False

    def run_one_case(self, case_id: int) -> dict:
        api_case_obj = ApiCase.objects.get(id=case_id)
        self.init(api_case_obj.project_id)
        self.result_init()
        self.__case_front(api_case_obj)
        case_api_list = self.get_case(case_id)
        if not case_api_list:
            raise CaseIsEmptyError(*ERROR_MSG_0008)
        for api_info in case_api_list:
            if not self.run_api(api_info):
                break
        self.api_case_result_sava(case_id)
        self.update_case_or_suite(case_id)
        if not self.is_batch:
            self.update_test_suite(self.case_status)
        else:
            ChatConsumer.active_send(SocketDataModel(
                code=200 if self.case_status == StatusEnum.SUCCESS.value else 300,
                msg=f'用例：{api_case_obj.name}，测试结果：{self.case_error_message}' if self.case_error_message else f'用例：{api_case_obj.name}测试成功',
                user=self.username,
                is_notice=ClientTypeEnum.WEB.value, ))
        self.__case_posterior(api_case_obj)
        return {
            'test_suite': self.test_suite_data['id'],
            'status': self.case_status,
            'error_message': self.case_error_message
        }

    def case_batch(self, case_list: list):
        self.is_batch = True
        case_result_list = []
        for case_id in case_list:
            self.run_one_case(case_id)
            case_result_list.append(self.case_status)
        if StatusEnum.FAIL.value in case_result_list:
            self.update_test_suite(StatusEnum.FAIL.value)
        else:
            self.update_test_suite(StatusEnum.SUCCESS.value)
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
            response: ResponseDataModel = self.http(request_data_model)
        except MangoServerError as error:
            self.case_error_message = error.msg
            self.save_test_result(case_detailed)
            return False
        try:
            # 断言
            self.assertion(response, case_detailed)
            # 后置处理
            self.posterior(response, case_detailed)
        except MangoServerError as error:
            self.case_error_message = error.msg
            self.save_test_result(case_detailed, request_data_model, response)
            return False
        self.case_status = StatusEnum.SUCCESS.value
        self.save_test_result(case_detailed, request_data_model, response)
        return True

    def get_case(self, case_id: int):
        if self.case_sort:
            return ApiCaseDetailed.objects.filter(case=case_id, case_sort__lte=self.case_sort).order_by('case_sort')
        else:
            return ApiCaseDetailed.objects.filter(case=case_id).order_by('case_sort')

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
