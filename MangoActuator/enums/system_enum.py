# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-05-06 8:34
# @Author : 毛鹏
from . import BaseEnum


class NoticeEnum(BaseEnum):
    """通知枚举"""
    MAIL = 0
    WECOM = 1
    NAILING = 2

    @classmethod
    def obj(cls):
        return {0: "邮箱", 1: "企微", 2: "钉钉-未测试"}


class EnvironmentEnum(BaseEnum):
    """测试环境枚举"""
    TEST = 0
    PRE = 1
    PRO = 2

    @classmethod
    def obj(cls):
        return {0: "测试环境", 1: "预发环境", 2: "生产环境"}


class AutoTestTypeEnum(BaseEnum):
    """自动测试类型"""
    UI = 0
    API = 1
    PERF = 2

    @classmethod
    def obj(cls):
        return {0: "界面", 1: "接口", 2: "性能"}


class CacheDataKey2Enum(BaseEnum):
    """缓存KEY的名称，不在系统设置页面展示"""
    PLAYWRIGHT_OPERATION_METHOD = 'playwright_operation_method'  # Playwright的操作
    UIAUTOMATOR_OPERATION_METHOD = 'uiautomator_operation_method'
    DESKTOP_OPERATION_METHOD = 'desktop_operation_method'
    IOS_OPERATION_METHOD = 'ios_operation_method'

    PLAYWRIGHT_ASSERTION_METHOD = 'playwright_assertion_method'
    UIAUTOMATOR_ASSERTION_METHOD = 'uiautomator_assertion_method'
    PUBLIC_ASSERTION_METHOD = 'public_assertion_method'
    SQL_ASSERTION_METHOD = 'sql_assertion_method'

    ASSERTION_METHOD = 'assertion_method'

    @classmethod
    def obj(cls):
        return {'DOMAIN_NAME': "本系统的URL地址"}
