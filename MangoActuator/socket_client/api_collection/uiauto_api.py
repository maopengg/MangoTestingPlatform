# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-29 11:20
# @Author : 毛鹏
from auto_ui.test_runner.case_distribution import CaseDistribution
from concurrent.futures.thread import ThreadPoolExecutor


class UiAutoApi:
    case = CaseDistribution()
    th = ThreadPoolExecutor(50)

    @classmethod
    def run_debug_case(cls, case_data: list[dict]):
        """
        执行调试用例对象浏览器对象
        @return:
        """
        cls.th.submit(cls.case.debug_case_distribution, case_data)

    @classmethod
    def run_debug_batch_case(cls, case_data: list[dict]):
        """
        执行调试用例对象浏览器对象
        @return:
        """
        cls.th.submit(cls.case.debug_case_distribution, case_data)

    @classmethod
    def run_group_case(cls, case_data: list[dict]):
        """
        执行并发对象浏览器对象
        @return:
        """
        cls.th.submit(cls.case.debug_case_distribution, case_data)

    @classmethod
    def run_group_batch_case(cls, case_data: list[dict]):
        """
        执行并发对象浏览器对象
        @return:
        """
        cls.th.submit(cls.case.debug_case_distribution, case_data)

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

    @classmethod
    def close_browser(cls):
        cls.case.page.close()


if __name__ == '__main__':
    import json

    r = UiAutoApi()
    with open(r'../../tests/debug_case.json', encoding='utf-8') as f:
        case_json = json.load(f)
        r.run_debug_case(case_json)
