# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-12-08 9:50
# @Author : 毛鹏

from src.enums import BaseEnum


class StatusEnum(BaseEnum):
    """状态枚举"""
    SUCCESS = 1
    FAIL = 0

    @classmethod
    def obj(cls):
        return {0: "关闭&失败", 1: "启用&通过"}


class TaskEnum(BaseEnum):
    """状态枚举"""
    FAIL = 0
    SUCCESS = 1
    STAY_BEGIN = 2
    PROCEED = 3

    @classmethod
    def obj(cls):
        return {0: "失败", 1: "通过", 2: "待开始", 3: "进行中"}


class ProductTypeEnum(BaseEnum):
    """影响api的接口"""
    WEB = 0
    PC = 1
    APP = 2
    ANDROID = 3
    IOS = 4
    MINI = 5

    @classmethod
    def obj(cls):
        return {
            0: "WEB（API,UI通用）",
            1: "PC桌面（API,UI通用）",
            2: "APP（API专用）",
            3: '安卓（UI专用）',
            4: 'IOS（UI专用）',
            5: '小程序（API专用）'
        }


class AutoTypeEnum(BaseEnum):
    """说明这个测试环境给那个自动化使用"""
    CURRENCY = 0
    UI = 1
    API = 2

    @classmethod
    def obj(cls):
        return {0: "前端&接口通用", 1: "前端自动化", 2: "接口自动化"}


class SystemEnvEnum(BaseEnum):
    MASTER = 'master'
    PROD = 'prod'
    DEV = 'dev'
    TEST = 'test'


class EnvironmentEnum(BaseEnum):
    """测试环境枚举"""
    TEST = 0
    PRE = 1
    PRO = 2
    DEV = 3
    UAT = 4
    SIM = 5

    @classmethod
    def obj(cls):
        return {0: "测试环境", 1: "预发环境", 2: "生产环境", 3: "开发环境", 4: "验收环境", 5: "仿真环境"}


class AutoTestTypeEnum(BaseEnum):
    """自动测试类型"""
    UI = 0
    API = 1
    PERF = 2
    OTHER = 3

    @classmethod
    def obj(cls):
        return {0: "前端", 1: "接口", 2: "性能", 3: "其他"}


class TestCaseTypeEnum(BaseEnum):
    """用例类型"""
    UI = 0
    API = 1
    PYTEST = 2

    @classmethod
    def obj(cls):
        return {0: "界面自动化", 1: "接口自动化", 2: "单元自动化"}


class CaseLevelEnum(BaseEnum):
    """测试用例级别"""
    P0 = 0
    P1 = 1
    P2 = 2
    P3 = 3

    @classmethod
    def obj(cls):
        return {0: "高", 1: "中", 2: "低", 3: "极低"}
