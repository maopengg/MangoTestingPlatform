# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/3/23 11:25
# @Author : 毛鹏

from PyAutoTest.utils.other_utils.decorator import convert_args


class PerfConsumer:

    @convert_args
    def perf_tst(self, team_name, case=1):
        pass
