# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/5/4 14:33
# @Author : 毛鹏

from auto_ui.test_runner.case_run_method import CaseRunMethod
from auto_ui.ui_tools.base_model import CaseGroupModel


class GroupCaseRun(CaseRunMethod):

    async def group_obj(self, group_case: CaseGroupModel):
        print(f'GroupCaseRun内存地址是：{id(self)}')
        # 获取组用例名称和组用例对象
        # group_case = collections.OrderedDict(group_case)
        # for group_name, group_value in group_case.items():
        # 获取每个用例
        for case_one in group_case.case_group:
            # 分给用例分发去执行
            await self.distribute_to_drivers(case_one)
        await self.close()

    async def test_res(self, response):
        print('用例执行结果,结果处理')

    async def close(self):
        await self.web.page.close()
