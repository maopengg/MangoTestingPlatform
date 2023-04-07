# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 处理所有用例的数据
# @Time   : 2023-03-12 10:54
# @Author : 毛鹏
import json

from PyAutoTest.auto_test.auto_system.models import TestObject
from PyAutoTest.auto_test.auto_ui.models import UiCase, RunSort, UiConfig
from PyAutoTest.auto_test.auto_ui.ui_tools.enum import End


class CaseData:

    def __init__(self, user):
        self.user = user

    def processing_use_cases(self, case_id: list or int, test_obj: int) -> list:
        a_use_case = []
        if isinstance(case_id, int):
            a_use_case.append(self.data_ui_case(test_obj, UiCase.objects.get(id=case_id).name))
        elif isinstance(case_id, list):
            for i in case_id:
                a_use_case.append(self.data_ui_case(test_obj, UiCase.objects.get(id=i).name))
        return a_use_case

    def data_ui_case(self, test_obj: int, case_name: str) -> dict:
        """
        根据test对象和用例ID返回一个UI测试对象回去
        @param test_obj: 测试环境id
        @param case_name: 用例id
        @return: 返回一个数据处理好的测试对象
        """
        case_ = UiCase.objects.get(name=case_name)
        data = {'case_id': case_name,
                'case_name': case_name,
                'case_url': TestObject.objects.get(id=test_obj).value + RunSort.objects.filter(
                    case_id=case_name).first().el_page.url}
        case_data = []
        run_sort = RunSort.objects.filter(case=case_name).order_by('run_sort')
        for i in run_sort:
            if i.el_name is None:
                case_data.append({
                    'ope_type': i.ope_type,
                    'ass_type': i.ass_type,
                    'ope_value': i.ope_value,
                    'ass_value': i.ass_value,
                    'ele_name': 'url' if case_.case_type == End.WEB.value else '小程序',
                    'ele_page_name': i.el_page.name,
                    'ele_exp': None,
                    'ele_loc': None,
                    'ele_sleep': 3,
                    'ele_sub': None
                })
                if case_.case_type == End.WEB.value:
                    data['local_port'], data['browser_path'] = self.__get_web_config()
                    data['type'] = End.WEB.value
                elif case_.case_type == End.APP.value:
                    data['equipment'], data['package'] = self.__get_app_config()
                    data['type'] = End.APP.value
            else:
                case_data.append({
                    'ope_type': i.ope_type,
                    'ass_type': i.ass_type,
                    'ope_value': i.ope_value,
                    'ass_value': i.ass_value,
                    'ele_name': i.el_name.name,
                    'ele_page_name': i.el_page.name,
                    'ele_exp': i.el_name.exp,
                    'ele_loc': i.el_name.loc,
                    'ele_sleep': i.el_name.sleep,
                    'ele_sub': i.el_name.sub
                })
        data['case_data'] = case_data
        return data

    def __get_web_config(self) -> tuple:
        user_ui_config = UiConfig.objects.get(user_id=self.user.get('id'))
        return user_ui_config.local_port, user_ui_config.browser_path

    def __get_app_config(self) -> tuple:
        user_ui_config = UiConfig.objects.get(user_id=self.user.get('id'))
        return user_ui_config.equipment, user_ui_config.package
