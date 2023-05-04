# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/5/4 14:33
# @Author : 毛鹏
from concurrent.futures.thread import ThreadPoolExecutor
from typing import Optional

from auto_ui.test_runner.case_run_method import CaseRunMethod
from auto_ui.test_runner.element_runner.web import WebRun


class GroupCaseRun(CaseRunMethod):

    def __init__(self):
        self.th = ThreadPoolExecutor(50)
        self.web: Optional[WebRun] = None
        # self.android: Optional[] = None

    async def group_case_distribution(self, data: list[dict]):
        """
        分发用例给不同的驱动进行执行
        @param data: 用例列表
        @return:
        """
        # 遍历list中的用例得到每个用例组
        for i in data:
            for group_name, group_value in i.items():
                for case_one in group_value:
                    await self.distribute_to_drivers(case_one)
                    #     只有用例组不为空的时候，才发送邮件，其他调式不发送通知！逻辑还没写

    async def close(self):
        await self.web.page.close()
