# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-29 11:20
# @Author : 毛鹏
from PyAutoTest.utils.other_utils.decorator import convert_args


class APIConsumer:
    @convert_args
    def api_test(self):
        pass
