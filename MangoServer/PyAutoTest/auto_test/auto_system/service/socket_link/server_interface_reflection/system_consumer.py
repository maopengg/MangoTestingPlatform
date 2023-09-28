# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023/3/23 11:25
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_system.service.notic_tools import notice_main


class SystemConsumer:

    def system_notice_main(self, project_name, case=1):
        """ 启动通知消息，自动进行通知 """
        notice_main(project_name, case)
        print('启动通知消息，自动进行通知')
