# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-05-06 8:34
# @Author : 毛鹏
from src.enums import BaseEnum


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
    OPEN = 'open'
    CLIENT_CONN_OBJ = 'client_obj'
    WEB_CONN_OBJ = 'web_obj'


class CacheDataKeyEnum(BaseEnum):
    """缓存KEY的名称"""
    DOMAIN_NAME = '本系统的URL地址'
    SEND_USER = '邮箱发送人'
    EMAIL_HOST = '邮箱域名'
    STAMP_KET = '邮箱的stamp_key'
    API_TIMEOUT = 'API请求超时时间'
    GIT_URL = 'git的请求url示例>https://{username}:{password}@gitee.com/mao-peng/MangoPytest.git'

    @classmethod
    def obj(cls):
        return {
            'DOMAIN_NAME': None,
            'SEND_USER': None,
            'EMAIL_HOST': None,
            'STAMP_KET': None,
            'API_TIMEOUT': 15,
            'GIT_URL': None
        }


class CacheDataKey2Enum(BaseEnum):
    """缓存KEY的名称，不在系统设置页面展示"""
    SELECT_VALUE = 'select_value'

    @classmethod
    def obj(cls):
        return {'DOMAIN_NAME': "本系统的URL地址"}
