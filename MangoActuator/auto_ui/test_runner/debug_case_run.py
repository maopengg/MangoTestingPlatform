# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/3/23 11:31
# @Author : 毛鹏
import json
from typing import Optional

from auto_ui.test_result.resulit_mian import ResultMain
from auto_ui.test_runner.case_run_method import CaseRunMethod
from auto_ui.test_runner.element_runner.web import WebRun


class CaseDistribution(CaseRunMethod):
    """
    用例分发
    """

    def __init__(self):
        self.web: Optional[WebRun] = None
        # self.android: Optional[] = None

    async def debug_case_distribution(self, data: list[dict]):
        """
        处理调试用例，开始用例对象，并调用分发用例方法
        @param data:
        @return:
        """
        for case_one in data:
            await self.distribute_to_drivers(case_one)
            # self.th.shutdown(True)
        await ResultMain.web_notice(200, '调试用例执行完成，请检查用例执行结果！')

    async def close(self):
        await self.web.page.close()


if __name__ == '__main__':
    # equipment1 = '7de23fdd'
    # package1 = 'com.tencent.mm'
    r = CaseDistribution()
    with open(r'../../tests/debug_case.json', encoding='utf-8') as f:
        case_json = json.load(f)
        r.debug_case_distribution(case_json)
