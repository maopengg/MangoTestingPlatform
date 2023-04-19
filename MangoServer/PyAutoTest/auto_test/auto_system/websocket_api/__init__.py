# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-09 11:14
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_system.notic_tools import notice_main


class MergeApi:

    @classmethod
    def notice_main_(cls, team_name, case=1):
        # return notice_main(team_name=None)
        notice_main(team_name, case)
