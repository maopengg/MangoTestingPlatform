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

    @classmethod
    def obj(cls):
        return {0: "界面", 1: "接口", 2: "性能"}


class CaseLevelEnum(BaseEnum):
    """测试用例级别"""
    P0 = 0
    P1 = 1
    P2 = 2
    P3 = 3

    @classmethod
    def obj(cls):
        return {0: "高", 1: "中", 2: "低", 3: "极低"}


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


class SocketEnum(BaseEnum):
    WEB_PATH = '/web/socket'
    CLIENT_PATH = '/client/socket'
    ADMIN = 'admin'
    CLIENT_CONN_OBJ = 'client_obj'
    WEB_CONN_OBJ = 'web_obj'


class CacheDataKeyEnum(BaseEnum):
    """缓存KEY的名称"""
    DOMAIN_NAME = '本系统的URL地址'
    SEND_USER = '邮箱发送人'
    EMAIL_HOST = '邮箱域名'
    STAMP_KET = '邮箱的stamp_key'
    API_TIMEOUT = 'API请求超时时间'

    @classmethod
    def obj(cls):
        return {
            'DOMAIN_NAME': None,
            'SEND_USER': None,
            'EMAIL_HOST': None,
            'STAMP_KET': None,
            'API_TIMEOUT': 15,
        }


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
