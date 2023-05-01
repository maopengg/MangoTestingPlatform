# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-29 11:20
# @Author : 毛鹏
from auto_ui.test_runner.case_distribution import CaseDistribution


class UiAutoApi:

    def run_debug_case(self, case_data: list[dict]):
        """
        执行调试用例对象浏览器对象
        @return:
        """
        CaseDistribution().case_distribution(case_data)


    def run_debug_batch_case(self, case_data: dict):
        """
        执行调试用例对象浏览器对象
        @return:
        """
        print('执行调试用例对象浏览器对象')
        print(case_data)

    def run_group_case(self, case_data: dict):
        """
        执行并发对象浏览器对象
        @return:
        """
        print(case_data)

    def run_group_batch_case(self, case_data: dict):
        """
        执行并发对象浏览器对象
        @return:
        """
        print(case_data)

    def new_chrome_browser_obj(self, case_data: dict):
        """
        实例化chrome浏览器对象
        @return:
        """
        print(case_data)

    def new_firefox_browser_obj(self, case_data: dict):
        """
        实例化firefox浏览器对象
        @return:
        """
        print(case_data)

