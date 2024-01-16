# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-07-07 10:14
# @Author : 毛鹏
from PyAutoTest.exceptions import MangoServerError


class UiConfigQueryIsNoneError(MangoServerError):

    def __init__(self, path):
        self.code = 301
        self.msg = path
