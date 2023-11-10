# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-07-15 13:22
# @Author : 毛鹏
class CacheIsNone(Exception):
    def __init__(self, msg):
        self.code = 301
        self.msg = msg
