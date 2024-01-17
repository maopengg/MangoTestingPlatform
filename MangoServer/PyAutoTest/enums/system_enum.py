# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-05-06 8:34
# @Author : 毛鹏
from PyAutoTest.enums import BaseEnum


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
