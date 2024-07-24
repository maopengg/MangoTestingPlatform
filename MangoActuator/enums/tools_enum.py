# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-12-08 9:50
# @Author : 毛鹏
from enum import Enum

from enums import BaseEnum


class ClientTypeEnum(BaseEnum):
    """
    三个端的类型
    """
    SERVER = 0
    WEB = 1
    ACTUATOR = 2

    @classmethod
    def obj(cls):
        return {0: "服务端", 1: "执行端", 2: "控制端"}


class ClientNameEnum(BaseEnum):
    """
    端名称
    """
    DRIVER = 'Mango Actuator'
    SERVER = 'Mango Server'
    WEB = 'mango-console'
    PLATFORM_CHINESE = '芒果自动化测试平台'
    PLATFORM_ENGLISH = 'MangoTestPlatform'

    @classmethod
    def obj(cls):
        return {'DRIVER': "Mango Actuator", 'SERVER': "Mango Server", 'WEB': "mango-console"}


class StatusEnum(BaseEnum):
    """状态枚举"""
    SUCCESS = 1
    FAIL = 0

    @classmethod
    def obj(cls):
        return {0: "关闭&进行中&失败", 1: "启用&已完成&通过"}


class CacheKeyEnum(Enum):
    """参数"""
    BROWSER_IS_MAXIMIZE = 'BROWSER_IS_MAXIMIZE'
    TEST_CASE_PARALLELISM = 'TEST_CASE_PARALLELISM'
    IS_RECORDING = 'IS_RECORDING'

class CacheValueTypeEnum(BaseEnum):
    """缓存数据类型"""
    STR = 0
    INT = 1
    FLOAT = 2
    BOOL = 3
    NONE = 4
    LIST = 5
    DICT = 6
    TUPLE = 7
    JSON = 8

    @classmethod
    def obj(cls):
        return {0: "字符串", 1: "整数", 2: "小数", 3: "布尔", 4: "null", 5: "列表", 6: "字典", 7: "元组", 8: "JSON"}


class SignalTypeEnum(BaseEnum):
    """缓存数据类型"""
    A = 0
    B = 1
    C = 2
    D = 3

    @classmethod
    def obj(cls):
        return {0: "字符串", 1: "整数", 2: "小数", 3: "用例展示"}
