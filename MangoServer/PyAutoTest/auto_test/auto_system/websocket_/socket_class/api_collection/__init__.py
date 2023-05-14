# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-29 11:19
# @Author : 毛鹏
import logging

from PyAutoTest.auto_test.auto_system.websocket_.socket_class.actuator_enum.self_test_class import SelfTestClass
from PyAutoTest.auto_test.auto_system.websocket_.socket_class.api_collection.apiauto_api import ApiAutoApi
from PyAutoTest.auto_test.auto_system.websocket_.socket_class.api_collection.command_api import CommandApi
from PyAutoTest.auto_test.auto_system.websocket_.socket_class.api_collection.uiauto_api import UiAutoApi

log = logging.getLogger('system')


class Collection(ApiAutoApi, UiAutoApi, CommandApi):

    def start_up(self, func, *args, **kwargs):
        try:
            getattr(self, func)(*args, **kwargs)
        except Exception as e:
            log.error(f'执行函数报错了，请检查函数{func}')


collection = Collection()
if __name__ == '__main__':
    collection.start_up(SelfTestClass.notice_main_.value, '应用组')
