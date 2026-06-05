# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-06-04 12:24
# @Author : 毛鹏
from src.common.enums import BaseEnum


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
    """全局变量类型"""
    CUSTOM = 0
    SQL = 1

    @classmethod
    def obj(cls):
        return {0: "自定义-第一加载", 1: "SQL-第二加载"}


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


class ApiAuthTypeEnum(BaseEnum):
    """API授权方式"""
    API = 0
    CUSTOM = 1

    @classmethod
    def obj(cls):
        return {0: "接口登录", 1: "自定义代码"}


class ApiAuthRefreshModeEnum(BaseEnum):
    """API授权刷新方式"""
    PASSIVE = 0
    TIMING = 1
    BOTH = 2
    MANUAL = 3

    @classmethod
    def obj(cls):
        return {0: "执行时检测刷新", 1: "定时刷新", 2: "执行时检测+定时刷新", 3: "手动刷新"}


class ApiAuthRefreshStatusEnum(BaseEnum):
    """API授权刷新状态"""
    INIT = 0
    SUCCESS = 1
    FAIL = 2

    @classmethod
    def obj(cls):
        return {0: "未刷新", 1: "刷新成功", 2: "刷新失败"}
