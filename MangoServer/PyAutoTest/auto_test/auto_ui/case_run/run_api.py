# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/4/28 11:56
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_system.consumers import ChatConsumer
from PyAutoTest.auto_test.auto_system.websocket_.socket_class.actuator_enum.ui_enum import UiEnum
from PyAutoTest.auto_test.auto_ui.case_run.case_data import CaseData
from PyAutoTest.auto_test.auto_ui.models import UiCaseGroup
from PyAutoTest.settings import DRIVER


class RunApi:

    @classmethod
    def __group_run(cls, group_id: int, username=None, time=False):
        """

        @param group_id: 用例组的ID
        @return:
        """
        case_group_data = UiCaseGroup.objects.get(pk=group_id)
        data = CaseData(case_group_data.timing_actuator.id)
        case_json = data.group_cases(case_group_data)
        if time:
            send_res = cls.run_case_send(username=case_group_data.timing_actuator.username,
                                         case_json=case_json,
                                         func_name=UiEnum.run_group_case.value)
            return send_res
        else:
            send_res = cls.run_case_send(username=username,
                                         case_json=case_json,
                                         func_name=UiEnum.run_group_case.value)
            return send_res

    @classmethod
    def group_batch(cls, group_id_list: list or int, username=None, time=False) -> object:
        """
        处理批量的请求
        @param group_id_list: 用例组的list或int
        @param time: 用来标识是不是定时任务
        @param username: 发送的用户
        @return:
        """
        case_group = []
        if isinstance(group_id_list, int):
            res = cls.__group_run(group_id_list, username, time)
            case_group.append(res)
            if not res.get('result'):
                return case_group, False
        elif isinstance(group_id_list, list):
            for group_id in group_id_list:
                res = cls.__group_run(group_id, username, time)
                case_group.append(res)
                if not res.get('result'):
                    return case_group, False
        return case_group, True

    @classmethod
    def __case_run(cls, environment: int, case_id: int, username):
        """
        调试用例单个执行
        """
        data = CaseData(username)
        case_data = data.data_ui_case(environment, case_id)
        send_res = cls.run_case_send(username=username,
                                     case_json=case_data,
                                     func_name=UiEnum.run_debug_case.value)
        return send_res

    @classmethod
    def case_run_batch(cls, case_list: int or list, environment: int, username):
        """
        调试用例批量执行
        @param case_list: 用例id列表或者一个
        @param environment: 测试环境
        @param username: websocket发送给的用户
        @return:
        """
        case_data = []
        if isinstance(case_list, int):
            res = cls.__case_run(environment, case_list, username)
            case_data.append(res)
            if not res.get('result'):
                return case_data, False
        elif isinstance(case_list, list):
            for case_id in case_list:
                res = cls.__case_run(environment, case_id, username)
                case_data.append(res)
                if not res.get('result'):
                    return case_data, False
        return case_data, True

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
