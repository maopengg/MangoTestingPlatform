# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-05-06 8:34
# @Author : 毛鹏
from src.common.enums import BaseEnum


class ClientTypeEnum(BaseEnum):
    """
    三个端的类型
    """
    SERVER = 0
    WEB = 1
    ACTUATOR = 2
    MCP = 3

    @classmethod
    def obj(cls):
        return {0: "芒果服务端", 1: "芒果用户端", 2: "芒果执行端", 3: "MCP"}


class ClientNameEnum(BaseEnum):
    """
    端名称
    """
    DRIVER = '测试平台执行器'
    SERVER = '测试平台服务器'
    WEB = '测试平台用户端'
    PLATFORM_CHINESE = '智书测试平台'
    PLATFORM_ENGLISH = 'MangoTestPlatform'

    @classmethod
    def obj(cls):
        return {'DRIVER': "芒果执行器", 'SERVER': "芒果服务器", 'WEB': "芒果用户端"}


class SocketEnum(BaseEnum):
    WEB_PATH = '/api/web/socket'
    CLIENT_PATH = '/api/client/socket'
    OPEN = 'open'
    CLIENT_CONN_OBJ = 'client_obj'
    WEB_CONN_OBJ = 'web_obj'


class CacheDataKeyEnum(BaseEnum):
    """缓存KEY的名称"""
    SYSTEM_DOMAIN_NAME = '本系统的URL地址'
    SYSTEM_SEND_USER = '邮箱发送人'
    SYSTEM_EMAIL_HOST = '邮箱域名'
    SYSTEM_STAMP_KET = '邮箱的stamp_key'
    API_TIMEOUT = 'API请求超时时间'
    PYTEST_GIT_URL = 'git的请求url示例>https://gitee.com/mao-peng/MangoPytest'
    PYTEST_GIT_USERNAME = 'git账号'
    PYTEST_GIT_PASSWORD = 'git密码'

    @classmethod
    def obj(cls):
        return {
            'SYSTEM_DOMAIN_NAME': None,
            'SYSTEM_SEND_USER': None,
            'SYSTEM_EMAIL_HOST': None,
            'SYSTEM_STAMP_KET': None,
            'API_TIMEOUT': 15,
            'PYTEST_GIT_URL': None,
            'PYTEST_GIT_USERNAME': None,
            'PYTEST_GIT_PASSWORD': None,
        }

    @classmethod
    def get_cache_value(cls, key):
        from src.apps.auto_system.models import CacheData
        return CacheData.objects.get(key=key.name).value


class CacheDataKey2Enum(BaseEnum):
    """缓存KEY的名称，不在系统设置页面展示"""
    PLAYWRIGHT_OPERATION_METHOD = 'playwright_operation_method'
    UIAUTOMATOR_OPERATION_METHOD = 'uiautomator_operation_method'
    DESKTOP_OPERATION_METHOD = 'desktop_operation_method'
    IOS_OPERATION_METHOD = 'ios_operation_method'
    PLAYWRIGHT_ASSERTION_METHOD = 'playwright_assertion_method'
    UIAUTOMATOR_ASSERTION_METHOD = 'uiautomator_assertion_method'
    PUBLIC_ASSERTION_METHOD = 'public_assertion_method'
    SQL_ASSERTION_METHOD = 'sql_assertion_method'
    ASSERTION_METHOD = 'assertion_method'
    SELECT_VALUE = 'select_value'
    ASS_SELECT_VALUE = 'ass_select_value'

    @classmethod
    def obj(cls):
        return {'DOMAIN_NAME': "本系统的URL地址"}


class TestSuiteNoticeEnum(BaseEnum):
    """缓存KEY的名称，不在系统设置页面展示"""
    NOT_SENT = 0
    SENT = 1
    EXPIRED = 2
    SENDING = 3

    @classmethod
    def obj(cls):
        return {
            cls.NOT_SENT.value: "等待发送",
            cls.SENT.value: "发送成功",
            cls.EXPIRED.value: "无需发送",
            cls.SENDING.value: "发送中",
        }
