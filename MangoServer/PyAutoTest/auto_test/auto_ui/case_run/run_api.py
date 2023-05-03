# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/4/28 11:56
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_ui.models import UiCaseGroup
from PyAutoTest.auto_test.auto_ui.case_run.case_data import CaseData


class RunApi:

    @classmethod
    def __group_run(cls, group_id: int, user):
        """

        @param group_id: 用例组的ID
        @param user: 用户属性
        @return:
        """
        group = UiCaseGroup.objects.get(id=group_id)
        data = CaseData(user)
        return data.group_cases(group)

    @classmethod
    def group_batch(cls, group_id_list: list or int, user):
        """
        处理批量的请求
        @param group_id_list: 用例组的list或int
        @param user: 用户属性
        @return:
        """
        case_group = []
        if isinstance(group_id_list, int):
            case_group.append(cls.__group_run(group_id_list, user))
        elif isinstance(group_id_list, list):
            for group_id in group_id_list:
                case_group.append(cls.__group_run(group_id, user))
        return case_group

    @classmethod
    def __case_run(cls, environment: int, case_id: int, user):
        data = CaseData(user)
        case_data = data.data_ui_case(environment, case_id)
        return case_data

    @classmethod
    def case_run_batch(cls, case_list: int or list, environment: int, user):
        case_data = []
        if isinstance(case_list, int):
            case_data.append(cls.__case_run(environment, case_list, user))
        elif isinstance(case_list, list):
            for case_id in case_list:
                case_data.append(cls.__case_run(environment, case_id, user))
        return case_data
