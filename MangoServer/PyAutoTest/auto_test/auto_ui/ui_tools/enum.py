# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2022-12-06 21:05
# @Author : 毛鹏
from enum import Enum


class End(Enum):
    """ 什么端 """
    WEB = 0
    APP = 1
    MINI = 2


class OpeType(Enum):
    """ {"0": "打开url"}，{"1": "点击"}，{"2": "输入"}，{"3": "截图"} """
    URL = 0
    CLICK = 1
    INPUT = 2
    CHART = 3


class Assertions(Enum):
    """ {"0": "-"}，{"1": "相等"}，{"2": "比元素大"}，{"3": "比元素小"} """
    NULL = 0
    EQUAL = 1
    LARGE = 2
    SMALL = 3


class WebExp(Enum):
    """ {0: "XPATH"}，{1: "ID"}，{2: "NAME"}，{3: "TEXT"} """
    XPATH = 0
    ID = 1
    NAME = 2
    TEXT = 3


class State(Enum):
    """ 0 是未测试，1 是失败，2 是通过"""
    NOT = 0
    FAIL = 1
    ADOPT = 2


if __name__ == '__main__':
    r = []
    for i in OpeType.__doc__.split("，"):
        for key, value in eval(i).items():
            r.append({
                'type': key,
                'dec': value
            })
    print(r)
