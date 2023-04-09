# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-09 11:14
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_system.websocket_api import MergeApi


class SocketAPI(MergeApi):

    def __init__(self, func_name, *args, **kwargs):
        getattr(self, func_name, )(*args, **kwargs)
