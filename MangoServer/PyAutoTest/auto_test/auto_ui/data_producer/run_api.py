# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/4/28 11:56
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_system.consumers import socket_conn
from PyAutoTest.auto_test.auto_ui.data_producer.case_data import CaseData
from PyAutoTest.auto_test.auto_ui.models import UiCaseGroup
from PyAutoTest.auto_test.auto_user.models import User
from PyAutoTest.base_data_model.system_data_model import SocketDataModel, QueueModel
from PyAutoTest.enums.actuator_api_enum import UiApiEnum
from PyAutoTest.enums.system_enum import SocketEnum
from PyAutoTest.settings import DRIVER


class RunApi:

    def __init__(self, username: str):
        self.username = username

    def __group_run(self, group_id: int, time=False):
        """

        @param group_id: 用例组的ID
        @return:
        """
        case_group_data = UiCaseGroup.objects.get(pk=group_id)
        if time:
            data = CaseData(case_group_data.timing_actuator.id)
            case_json = data.group_cases(case_group_data)
            send_res = self.run_case_send(case_json=case_json,
                                          func_name=UiApiEnum.run_group_case.value)
        else:
            data = CaseData(User.objects.get(username=self.username).id)
            case_json = data.group_cases(case_group_data)
            send_res = self.run_case_send(case_json=case_json,
                                          func_name=UiApiEnum.run_group_case.value)
        return case_json, send_res

    def group_batch(self, group_id_list: list or int, time=False):
        """
        处理批量的请求
        @param group_id_list: 用例组的list或int
        @param time: 用来标识是不是定时任务
        @return:
        """
        case_group = []
        if isinstance(group_id_list, int):
            case_json, send_res = self.__group_run(group_id_list, time)
            case_group.append(case_json)
            if send_res:
                return case_group, True
        elif isinstance(group_id_list, list):
            for group_id in group_id_list:
                case_json, send_res = self.__group_run(group_id, time)
                case_group.append(case_json)
                if send_res:
                    return case_group, True
        return case_group, False

    def __case_run(self, te: int, case_id: int, user_id):
        """
        调试用例单个执行
        """
        data = CaseData(user_id)
        case_data = data.data_ui_case(te, case_id)
        send_res = self.run_case_send(case_json=case_data,
                                      func_name=UiApiEnum.run_debug_case.value)
        return case_data, send_res

    def case_run_batch(self, case_list: int or list, te: int, user_id):
        """
        调试用例批量执行
        @param case_list: 用例id列表或者一个
        @param te: 测试环境
        @param user_id: user_id
        @return:
        """
        case_data = []
        if isinstance(case_list, int):
            case_json, send_res = self.__case_run(te, case_list, user_id)
            case_data.append(case_json)
            if send_res:
                return case_data, False
        elif isinstance(case_list, list):
            for case_id in case_list:
                case_json, send_res = self.__case_run(te, case_id, user_id)
                case_data.append(case_json)
                if send_res:
                    return case_data, False
        return case_data, True

    def run_case_send(self, case_json, func_name: str) -> bool:
        """
        发送给第三方工具方法
        @param case_json: 需要发送的json数据
        @param func_name: 需要执行的函数
        @return:
        """

        return socket_conn.active_send(SocketDataModel(
            code=200,
            msg=f'{DRIVER}：收到用例数据，准备开始执行自动化任务！',
            user=self.username,
            client=SocketEnum.client_path.value,
            func=func_name,
            data=QueueModel(func_name=func_name, func_args=case_json),
        ))
