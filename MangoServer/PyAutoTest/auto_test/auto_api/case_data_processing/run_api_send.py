# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-06-04 12:24
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_api.models import ApiCase
from PyAutoTest.auto_test.auto_api.views.api_case import ApiCaseSerializers
from PyAutoTest.auto_test.auto_system.consumers import ChatConsumer
from PyAutoTest.auto_test.auto_system.models import TestObject
from PyAutoTest.auto_test.auto_system.websocket_.socket_class.actuator_enum.api_enum import ApiEnum
from PyAutoTest.settings import DRIVER


class RunApiSend:

    @classmethod
    def get_api_case_data(cls, case_id: int) -> dict:
        case_data = ApiCase.objects.get(id=case_id)
        return ApiCaseSerializers(case_data).data

    @classmethod
    def get_api_case_url(cls, run_obj: int) -> str:
        return TestObject.objects.get(id=run_obj).value

    @classmethod
    def use_group_case(cls, case_id: int, run_obj: int) -> dict:
        case_dict = cls.get_api_case_data(case_id)
        url = cls.get_api_case_url(run_obj)
        return {
            'case_url': url,
            'case_data': case_dict,
        }

    @classmethod
    def group_case_list(cls, case_list: list, run_obj: int, username: int) -> dict or bool:
        send_res = cls.run_case_send(username=username,
                                     case_json={
                                         'is_group': False,
                                         'group_name': '',
                                         'group_case': [cls.use_group_case(case_id, run_obj)
                                                        for case_id in case_list]
                                     },
                                     func_name=ApiEnum.api_case_run.value)
        return send_res, send_res.get('result')

    @classmethod
    def run_case_send(cls, username, case_json, func_name: str) -> dict:
        """
        发送给第三方工具方法
        @param username: 发送给执行器的用户
        @param case_json: 需要发送的json数据
        @param func_name: 需要执行的函数
        @return:
        """
        server = ChatConsumer()
        f = server.active_send(
            code=200,
            func=func_name,
            user=username,
            msg=f'{DRIVER}：收到用例数据，准备开始执行自动化任务！',
            data=case_json,
            end='client_obj'
        )
        if f is True:
            return {'result': True,
                    "case_data": case_json}

        else:
            return {'result': False,
                    "case_data": case_json}
