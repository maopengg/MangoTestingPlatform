# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023/3/23 11:25
# @Author : 毛鹏
import json

from PyAutoTest.auto_test.auto_system.service.notic_tools import NoticeMain
from PyAutoTest.tools.cache_utils.redis_base import RedisBase


class SystemConsumer:

    def system_notice_main(self, project_name, case=1):
        """ 启动通知消息，自动进行通知 """
        NoticeMain.test_notice_send(case)
        print('启动通知消息，自动进行通知')

    def t_set_redis(self, data: list[dict]):
        redis = RedisBase('default')
        for i in data:
            for key, value in i.items():
                redis.set_key(key, value)
