# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2022-12-06 21:05
# @Author : 毛鹏
import types
from enum import Enum, unique
from typing import Dict, Text, Callable


class End(Enum):
    """ {"0": "WEB"}，{"1": "APP"}，{"2": "MINI"} """
    WEB = 0
    APP = 1
    MINI = 2


class Api(Enum):
    HEAD = "head"
    BODY = "body"


class OpeType(Enum):
    """ [NULL, JSON] """
    NULL = 0
    JSON = 1


class Method(Enum):
    """ [NULL, JSON] """
    GET = 0
    POST = 1
    PUT = 2
    DELETE = 3
    OPTIONS = 4
    DEAD = 5
    PATCH = 6


class PublicRelyType(Enum):
    """ {"0": "CUSTOM"}，{"1": "SQL"}，{"2": "HEAD"} """
    CUSTOM = 0
    SQL = 1
    HEAD = 2


class State(Enum):
    """0是未测试，1是通过，2是失败"""
    NOTTEST = 0
    ADOPT = 1
    FAIL = 2


class ApiType(Enum):
    """0是本期接口，1是用例调试，2是测试用例"""
    stage = 0
    debug = 1
    test = 2


@unique
class AssertMethod(Enum):
    """断言类型"""
    equals = "=="
    less_than = "lt"
    less_than_or_equals = "le"
    greater_than = "gt"
    greater_than_or_equals = "ge"
    not_equals = "not_eq"
    string_equals = "str_eq"
    length_equals = "len_eq"
    length_greater_than = "len_gt"
    length_greater_than_or_equals = 'len_ge'
    length_less_than = "len_lt"
    length_less_than_or_equals = 'len_le'
    contains = "contains"
    contained_by = 'contained_by'
    startswith = 'startswith'
    endswith = 'endswith'


def load_module_functions(module) -> Dict[Text, Callable]:
    """ 获取 module中方法的名称和所在的内存地址 """
    module_functions = {}

    for name, item in vars(module).items():
        if isinstance(item, types.FunctionType):
            module_functions[name] = item
    return module_functions


if __name__ == '__main__':
    # case = 0
    # lis = [x.name for x in Method if x.value == case][0]
    # print(type(lis), lis)
    # for i in Method:
    #     if i.value == 1:
    #         print(i.name)
    # print(Method.name)
    for name, obj in Method.__members__.items():
        print(name + ':', obj)
        print(obj.name, obj.value)
