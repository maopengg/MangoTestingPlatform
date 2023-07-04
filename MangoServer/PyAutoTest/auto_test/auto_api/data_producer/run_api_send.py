# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-06-04 12:24
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_api.models import ApiPublic, ApiCase
from PyAutoTest.auto_test.auto_system.consumers import ChatConsumer
from PyAutoTest.auto_test.auto_system.models import TestObject
from PyAutoTest.base_data_model.api_data_model import PublicModel, CaseGroupModel, RequestModel
from PyAutoTest.enums.actuator_api_enum import ApiApiEnum
from PyAutoTest.settings import DRIVER


class RunApiSend:
    def __init__(self, username: str, test_obj: int = None):
        self.username = username
        if test_obj:
            self.host = TestObject.objects.get(id=int(test_obj)).value

    def public_args_data(self):
        """
        处理公共数据
        """
        objects_filter = ApiPublic.objects.filter(state=1, type=0)
        public_args_list = []
        for obj in objects_filter:
            public_args_model = PublicModel(
                end=obj.end,
                public_type=obj.public_type,
                name=obj.name,
                key=obj.key,
                value=obj.value
            )
            public_args_dict = public_args_model.dict()
            public_args_list.append(public_args_dict)
        return public_args_list, self.case_send(public_args_list, ApiApiEnum.refresh_cache.value)

    def request_data(self, case_id: int, send: bool = False):
        """
        处理一个用力请求数据
        """
        case = ApiCase.objects.get(id=case_id)
        case_json = RequestModel(case_id=case.id,
                                 case_name=case.name,
                                 url=self.host + case.url,
                                 method=case.method,
                                 header=case.header,
                                 body_type=case.body_type,
                                 body=case.body).dict()
        if self.username and send:
            return case_json, self.case_send(case_json, ApiApiEnum.api_debug_case.value)
        return case_json, False

    def batch_requests_data(self, case_list: list):
        """
        批量请求
        """
        case_json = [self.request_data(i)[0] for i in case_list]
        return case_json, self.case_send(case_json, ApiApiEnum.api_batch_case.value)

    def group_case_data(self, group_name, case_list: list):
        """
        用例组数据
        """
        case_json = CaseGroupModel(
            group_name=group_name,
            case_group_list=[self.request_data(i)[0] for i in case_list]).dict()
        return case_json, self.case_send(case_json, ApiApiEnum.api_group_case.value)

    def case_send(self, case_json, func_name: str):
        """
        发送给第三方工具方法
        @param case_json: 需要发送的json数据
        @param func_name: 需要执行的函数
        @return:
        """
        server = ChatConsumer()
        f = server.active_send(
            code=200,
            func=func_name,
            user=self.username,
            msg=f'{DRIVER}：收到用例数据，准备开始执行自动化任务！',
            data=case_json,
            end='client_obj'
        )
        return True if f else False
