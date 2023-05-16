# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/4/28 11:56
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_system.consumers import ChatConsumer
from PyAutoTest.auto_test.auto_system.websocket_.socket_class.actuator_enum.ui_enum import UiEnum
from PyAutoTest.auto_test.auto_ui.case_run.case_data import CaseData
from PyAutoTest.auto_test.auto_ui.models import UiCaseGroup
from PyAutoTest.auto_test.auto_user.models import User
from PyAutoTest.settings import DRIVER


class RunApi:

    @classmethod
    def __group_run(cls, group_id: int, username=None, time=False):
        """

        @param group_id: 用例组的ID
        @return:
        """
        case_group_data = UiCaseGroup.objects.get(pk=group_id)
        if time:
            data = CaseData(case_group_data.timing_actuator.id)
            case_json = data.group_cases(case_group_data)
            send_res = cls.run_case_send(username=case_group_data.timing_actuator.username,
                                         case_json=case_json,
                                         func_name=UiEnum.run_group_case.value)
            return send_res
        else:
            data = CaseData(User.objects.get(username=username).id)
            case_json = data.group_cases(case_group_data)
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
    def __case_run(cls, te: int, case_id: int, user):
        """
        调试用例单个执行
        """
        data = CaseData(user.get('id'))
        case_data = data.data_ui_case(te, case_id)
        send_res = cls.run_case_send(username=user.get('username'),
                                     case_json=case_data,
                                     func_name=UiEnum.run_debug_case.value)
        return send_res

    @classmethod
    def case_run_batch(cls, case_list: int or list, te: int, user):
        """
        调试用例批量执行
        @param case_list: 用例id列表或者一个
        @param te: 测试环境
        @param user: websocket发送给的用户
        @return:
        """
        case_data = []
        if isinstance(case_list, int):
            res = cls.__case_run(te, case_list, user)
            case_data.append(res)
            if not res.get('result'):
                return case_data, False
        elif isinstance(case_list, list):
            for case_id in case_list:
                res = cls.__case_run(te, case_id, user)
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
