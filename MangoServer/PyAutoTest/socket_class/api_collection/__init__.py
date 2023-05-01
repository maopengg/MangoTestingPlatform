# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-29 11:19
# @Author : 毛鹏
import apiauto_api
import uiauto_api
import command_api
from PyAutoTest.socket_class.actuator_enum.self_test_class import SelfTestClass


class Collection(apiauto_api.ApiAutoApi, uiauto_api.UiAutoApi, command_api.CommandApi):

    def start_up(self, func, *args, **kwargs):
        getattr(self, func)(*args, **kwargs)


collection = Collection()
if __name__ == '__main__':
    collection.start_up(SelfTestClass.notice_main_.value, '应用组')
