# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-25 11:52
# @Author : 毛鹏
from tests.demo3 import A


class B(A):
    def __init__(self):
        super().__init__()  # 调用 A 的构造函数

    def b(self, extra_value):
        print('b', self.value, extra_value)
