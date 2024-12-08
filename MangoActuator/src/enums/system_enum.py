# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-05-06 8:34
# @Author : 毛鹏
from . import BaseEnum


class ClientTypeEnum(BaseEnum):
    """
    三个端的类型
    """
    SERVER = 0
    WEB = 1
    ACTUATOR = 2

    @classmethod
    def obj(cls):
        return {0: "服务端", 1: "控制端", 2: "执行端"}


class ClientNameEnum(BaseEnum):
    """
    端名称
    """
    DRIVER = 'Mango Actuator'
    SERVER = 'Mango Server'
    WEB = 'mango-console'
    PLATFORM_CHINESE = '芒果测试平台'
    PLATFORM_ENGLISH = 'MangoTestPlatform'

    @classmethod
    def obj(cls):
        return {'DRIVER': "Mango Actuator", 'SERVER': "Mango Server", 'WEB': "mango-console"}


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
