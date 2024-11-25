# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-12-11 16:16
# @Author : 毛鹏
import traceback
from urllib.parse import urljoin

from PyAutoTest.auto_test.auto_api.models import ApiCaseDetailed, ApiCase, ApiInfo
from PyAutoTest.auto_test.auto_api.service.base_tools.case_detailed import CaseDetailedInit
from PyAutoTest.auto_test.auto_system.consumers import ChatConsumer
from PyAutoTest.auto_test.auto_user.models import User
from PyAutoTest.enums.api_enum import MethodEnum
from PyAutoTest.enums.tools_enum import StatusEnum, ClientTypeEnum
from PyAutoTest.exceptions import *
from PyAutoTest.models.api_model import RequestDataModel, ResponseDataModel
from PyAutoTest.models.socket_model import SocketDataModel
from PyAutoTest.tools.assertion.public_assertion import PublicAssertion


class ApiCaseRun(CaseDetailedInit, PublicAssertion):

    def test_case(self, case_id: int, case_sort: int | None = None) -> dict:
        api_case = ApiCase.objects.get(id=case_id)
        self.project_product_id = api_case.project_product.id
        self.init_test_object()
        self.init_public()
        self.init_case_front(api_case)
        self.case_detailed(case_id, case_sort)
        self.init_case_posterior(api_case)
        self.update_test_case(case_id, self.status, self.result_data.model_dump())
        self.send_notice(api_case.name)
        return self.result_data.model_dump()

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
        try:
            for i in case_detailed_list:
                self.front_sql(i)
                request_data_model = RequestDataModel(method=MethodEnum(i.api_info.method).name,
                                                      url=urljoin(self.test_object.value, i.url),
                                                      headers=i.header,
                                                      params=i.params,
                                                      data=i.data,
                                                      json_data=i.json,
                                                      file=i.file)
                response: ResponseDataModel = self.send_request(request_data_model)
                self.assertion(response, i)
                self.posterior(response, i)
        except MangoServerError as error:
            self.status = StatusEnum.FAIL
            self.error_message = error.msg
        except Exception as error:
            traceback.print_exc()
            self.status = StatusEnum.FAIL
            log.api.error(error)
            self.error_message = f'发生未知错误，请联系管理员来处理异常，异常内容：{error}'
        else:
            self.status = StatusEnum.SUCCESS

    def send_notice(self, case_name: str, ):
        if self.is_notice:
            ChatConsumer.active_send(SocketDataModel(
                code=200 if self.status == StatusEnum.SUCCESS.value else 300,
                msg=f'用例：{case_name}，测试结果：{self.error_message}' if self.error_message else f'用例：{case_name}测试成功',
                user=User.objects.get(id=self.user_id).username,
                is_notice=ClientTypeEnum.WEB.value, ))

    @classmethod
    def update_api_info(cls, api_info_id: int, status: StatusEnum):
        api_info_obj = ApiInfo.objects.get(id=api_info_id)
        api_info_obj.status = status.value
        api_info_obj.save()

    @classmethod
    def update_test_case(cls, case_id: int, status: StatusEnum, result_data: dict):
        api_case = ApiCase.objects.get(id=case_id)
        api_case.result_data = result_data
        api_case.status = status.value
        api_case.save()

    @classmethod
    def update_case_detailed(cls, case_detailed_id: int, status: StatusEnum):
        api_info_obj = ApiCaseDetailed.objects.get(id=case_detailed_id)
        api_info_obj.status = status.value
        api_info_obj.save()
