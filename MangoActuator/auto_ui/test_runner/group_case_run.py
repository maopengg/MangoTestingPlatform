# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/5/4 14:33
# @Author : 毛鹏
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from auto_ui.test_runner.case_run_method import CaseRunMethod
from auto_ui.test_runner.element_runner.web import WebRun


class GroupCaseRun(CaseRunMethod):

    def __init__(self):
        self.web: Optional[WebRun] = None
        # self.android: Optional[] = None

    async def group_case_decompose(self, data: list[dict]):
        """
        分发用例给不同的驱动进行执行
        @param data: 用例列表
        @return:
        """
        tasks = [self.job(task) for task in data]
        # 并发执行任务
        await asyncio.gather(*tasks)
        # group = []
        # # 遍历list中的用例得到每个用例组
        # for i in data:
        #     # 获取组用例名称和组用例对象
        #     with ThreadPoolExecutor(10) as executor:
        #         future = executor.submit(self.group_obj, i)
        #         result = await asyncio.wrap_future(future)
        #         self.test_res(result)

        # await self.group_obj(i)

    async def group_obj(self, group_case: dict):
        # 获取组用例名称和组用例对象
        for group_name, group_value in group_case.items():
            # 获取每个用例
            for case_one in group_value:
                # 分给用例分发去执行
                await self.distribute_to_drivers(case_one)
        await self.close()

    def test_res(self, response):
        print(response)

    async def close(self):
        await self.web.page.close()

    async def job(self, task):
        # 在协程中使用线程池执行任务
        with ThreadPoolExecutor(10) as executor:
            # 将任务提交给线程池
            future = executor.submit(self.group_obj, task)
            # 等待任务完成
            result = await asyncio.wrap_future(future)
            # 处理任务结果
            self.test_res(result)


if __name__ == '__main__':
    import asyncio
    import json

    r = GroupCaseRun()
    with open(r'../../tests/group_case.json', encoding='utf-8') as f:
        case_json = json.load(f)
        loop = asyncio.new_event_loop()  # 创建新的事件循环
        asyncio.set_event_loop(loop)  # 设置新的事件循环为当前事件循环
        p = loop.run_until_complete(r.group_case_decompose(case_json.get('data')))  # 运行事件循环
