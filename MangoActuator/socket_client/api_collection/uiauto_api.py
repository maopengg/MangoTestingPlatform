# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-29 11:20
# @Author : 毛鹏
from auto_ui.test_runner.case_distribution import CaseDistribution
from threading import Thread


class UiAutoApi:
    case = CaseDistribution()

    @classmethod
    def run_debug_case(cls, case_data: list[dict]):
        """
        执行调试用例对象浏览器对象
        @return:
        """
        t = Thread(target=cls.case.debug_case_distribution, args=(case_data,))
        t.start()
        print('主线程')
        t.join()

    @classmethod
    def run_debug_batch_case(cls, case_data: list[dict]):
        """
        执行调试用例对象浏览器对象
        @return:
        """
        cls.case.debug_case_distribution(case_data)

    @classmethod
    def run_group_case(cls, case_data: list[dict]):
        """
        执行并发对象浏览器对象
        @return:
        """
        print(case_data)

    @classmethod
    def run_group_batch_case(cls, case_data: list[dict]):
        """
        执行并发对象浏览器对象
        @return:
        """
        print(case_data)

    @classmethod
    def new_chrome_browser_obj(cls, case_data: list[dict]):
        """
        实例化chrome浏览器对象
        @return:
        """
        print(case_data)

    @classmethod
    def new_firefox_browser_obj(cls, case_data: list[dict]):
        """
        实例化firefox浏览器对象
        @return:
        """
        print(case_data)
