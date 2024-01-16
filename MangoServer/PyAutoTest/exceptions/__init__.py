# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-07-07 10:14
# @Author : 毛鹏

class MangoServerError(Exception):

    def __init__(self):
        self.code = None
        self.msg = None
