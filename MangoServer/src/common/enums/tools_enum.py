# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-12-08 9:50
# @Author : 毛鹏

from src.common.enums import BaseEnum


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
        return {0: "界面&接口通用", 1: "界面自动化", 2: "接口自动化"}


class DatabaseTypeEnum(BaseEnum):
    """数据库类型枚举"""
    MYSQL = 0
    POSTGRESQL = 1
    SQLITE = 2
    ORACLE = 3
    SQLSERVER = 4

    @classmethod
    def obj(cls):
        return {
            0: "MySQL",
            1: "PostgreSQL",
            2: "SQLite",
            3: "Oracle",
            4: "SQL Server",
        }


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


class TestCaseTypeEnum(BaseEnum):
    """用例类型"""
    UI = 0
    API = 1
    PYTEST = 2
    OTHER = 3

    @classmethod
    def obj(cls):
        return {0: "界面自动化", 1: "接口自动化", 2: "单元自动化", 3: "其他自动化"}


class CaseLevelEnum(BaseEnum):
    """测试用例级别"""
    P0 = 0
    P1 = 1
    P2 = 2
    P3 = 3

    @classmethod
    def obj(cls):
        return {0: "高", 1: "中", 2: "低", 3: "极低"}


class ApiCaseScenarioTypeEnum(BaseEnum):
    """API 用例场景类型"""
    NORMAL = 0
    EXCEPTION = 1
    BOUNDARY = 2
    PERMISSION = 3
    DATA = 4
    FLOW = 5

    @classmethod
    def obj(cls):
        return {
            0: "正常场景",
            1: "异常场景",
            2: "边界场景",
            3: "权限场景",
            4: "数据场景",
            5: "流程场景",
        }


class ApiCaseScenarioLayerEnum(BaseEnum):
    """API 用例场景层级"""
    API = 0
    INTEGRATION = 1
    E2E = 2

    @classmethod
    def obj(cls):
        return {
            0: "接口/组件层",
            1: "Integration集成",
            2: "E2E端到端",
        }


class ApiCaseScenarioTagEnum(BaseEnum):
    """API 用例场景标签"""
    SMOKE = 0
    REGRESSION = 1
    MAIN_FLOW = 2
    CORE_LINK = 3
    HIGH_FREQUENCY = 4
    BLOCKING = 5
    ONLINE_INSPECTION = 6

    @classmethod
    def obj(cls):
        return {
            0: "冒烟",
            1: "回归",
            2: "主流程",
            3: "核心链路",
            4: "高频",
            5: "阻塞",
            6: "线上巡检",
        }
