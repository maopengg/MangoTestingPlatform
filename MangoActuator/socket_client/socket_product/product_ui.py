# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-29 11:20
# @Author : 毛鹏
from queue import Queue
from typing import Optional

from auto_ui.test_runner.debug_case_run import CaseDistribution


class UiAutoApi:
    case = CaseDistribution()

    def __init__(self):
        self.qu: Optional[Queue] = None

    def run_debug_case(self, case_data: list[dict]):
        """
        处理debug_case的用例数据
        @return:
        """
        for i in case_data:
            self.qu.put({'debug_case': i})

    def run_group_case(self, case_data: list[dict]):
        """
        执行并发对象浏览器对象
        @return:
        """
        for i in case_data:
            self.qu.put({'web_group_case': i})


if __name__ == '__main__':
    pass
