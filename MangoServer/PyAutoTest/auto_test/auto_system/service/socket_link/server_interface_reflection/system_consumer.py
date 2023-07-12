# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/3/23 11:25
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_system.service.notic_tools import notice_main
from PyAutoTest.utils.other_utils.decorator import convert_args


class SystemConsumer:

    @convert_args
    def system_notice_main(self, team_name, case=1):
        """ 启动通知消息，自动进行通知 """
        notice_main(team_name, case)
        print('启动通知消息，自动进行通知')
