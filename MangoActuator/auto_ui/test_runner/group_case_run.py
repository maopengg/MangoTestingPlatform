# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/5/4 14:33
# @Author : 毛鹏

import asyncio
from typing import Optional

from auto_ui.test_runner.case_run_method import CaseRunMethod
from auto_ui.test_runner.element_runner.web import WebRun


class GroupCaseRun:

    @classmethod
    def group_case_decompose(cls, data: list[dict]):
        """
        分发用例给不同的驱动进行执行
        @param data: 用例列表
        @return:
        """
        task_list = []
        for i in data:
            task_list.append(asyncio.create_task(GroupCaseRunR().group_obj(i)))
        res = asyncio.wait(task_list, timeout=None)
        # res = await asyncio.gather(i for i in task_list)
        print(res)


class GroupCaseRunR(CaseRunMethod):

    def __init__(self):
        self.web: Optional[WebRun] = None

    async def group_obj(self, group_case: dict):
        print(id(self))
        # 获取组用例名称和组用例对象
        for group_name, group_value in group_case.items():
            # 获取每个用例
            for case_one in group_value:
                # 分给用例分发去执行
                await self.distribute_to_drivers(case_one)
        await self.close()

    def test_res(self, response):
        print('用例执行结果', response)

    async def close(self):
        await self.web.page.close()


if __name__ == '__main__':
    pass
