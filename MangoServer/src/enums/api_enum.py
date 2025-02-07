# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-06-04 12:24
# @Author : 毛鹏
from src.enums import BaseEnum


class ApiClientEnum(BaseEnum):
    """设备类型"""
    WEB = 0
    APP = 1
    PC = 2
    MINI = 3

    @classmethod
    def obj(cls):
        return {0: "WEB", 1: "PC桌面", 2: "APP", 3: "小程序", }


class MethodEnum(BaseEnum):
    """方法枚举"""
    GET = 0
    POST = 1
    PUT = 2
    DELETE = 3
    OPTIONS = 4
    DEAD = 5
    PATCH = 6

    @classmethod
    def obj(cls):
        return {0: "GET", 1: "POST", 2: "PUT", 3: "DELETE", 4: "OPTIONS", 5: "DEAD", 6: "PATCH"}


class ApiPublicTypeEnum(BaseEnum):
    """公共参数类型"""
    CUSTOM = 0
    SQL = 1
    LOGIN = 2

    @classmethod
    def obj(cls):
        return {0: "自定义-第一加载", 1: "SQL-第二加载", 2: "登录-第三加载", }


class ApiTypeEnum(BaseEnum):
    """接口类型"""
    batch = 0
    debug = 1
    success = 2

    @classmethod
    def obj(cls):
        return {0: "批量生成", 1: "调试接口", 2: "调试完成"}


class ApiParameterTypeEnum(BaseEnum):
    """api请求参数的类型"""
    params = 0
    data = 1
    json = 2
    file = 3

    @classmethod
    def obj(cls):
        return {0: "参数", 1: "表单", 2: "json", 3: "文件"}
