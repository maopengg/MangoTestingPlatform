# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-29 11:20
# @Author : 毛鹏
import asyncio

from auto_ui.test_runner.debug_case_run import CaseDistribution
from auto_ui.test_runner.group_case_run import GroupCaseRun


class UiAutoApi:
    case = CaseDistribution()

    # loop = asyncio.new_event_loop()  # 创建新的事件循环
    # asyncio.set_event_loop(loop)

    @classmethod
    def run_debug_case(cls, case_data: list[dict]):
        """
        执行调试用例对象浏览器对象
        @return:
        """
        # cls.th.submit(cls.case.debug_case_distribution, case_data)
        asyncio.create_task(cls.case.debug_case_distribution(case_data))

    @classmethod
    def run_group_case(cls, case_data: list[dict]):
        """
        执行并发对象浏览器对象
        @return:
        """
        asyncio.create_task(GroupCaseRun().group_case_decompose(case_data))

    @classmethod
    def run_group_batch_case(cls, case_data: list[dict]):
        """
        执行并发对象浏览器对象
        @return:
        """
        asyncio.create_task(GroupCaseRun().group_case_decompose(case_data))

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
    with open(r'../../tests/group_case.json', encoding='utf-8') as f:
        case_json = json.load(f)
        import asyncio
        loop = asyncio.new_event_loop()  # 创建新的事件循环
        asyncio.set_event_loop(loop)  # 设置新的事件循环为当前事件循环
        p = loop.run_until_complete(r.run_group_case(case_json))  # 运行事件循环
