# -*- coding: utf-8 -*-
# @Project: api
# @Description: 
# @Time   : 2022-12-06 21:05
# @Author : 毛鹏
from enum import Enum


class ClientEnum(Enum):
    """ {"0": "WEB"}，{"1": "APP"}，{"2": "MINI"} """
    WEB = 0
    APP = 1
    MINI = 2


class BodyTypeEnum(Enum):
    """ [NULL, JSON] """
    NULL = 0
    JSON = 1


class MethodEnum(Enum):
    """ [NULL, JSON] """
    GET = 0
    POST = 1
    PUT = 2
    DELETE = 3
    OPTIONS = 4
    DEAD = 5
    PATCH = 6


class ApiPublicTypeEnum(Enum):
    """ {"0": "登录"}，{"1": "自定义"}，{"2": "SQL"}，{"2": "请求头"} """
    LOGIN = 0
    CUSTOM = 1
    SQL = 2
    HEADER = 3


class StateEnum(Enum):
    """0是未测试，1是通过，2是失败"""
    UNTESTED = 0
    ADOPT = 1
    FAIL = 2


class ApiTypeEnum(Enum):
    """0是本期接口，1是用例调试，2是测试用例"""
    stage = 0
    debug = 1
    test = 2


if __name__ == '__main__':
    # case = 0
    # lis = [x.name for x in Method if x.value == case][0]
    # print(type(lis), lis)
    # for i in Method:
    #     if i.value == 1:
    #         print(i.name)
    # print(Method.name)
    for name, obj in MethodEnum.__members__.items():
        print(name + ':', obj)
        print(obj.name, obj.value)
