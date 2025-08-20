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
        return {0: "芒果服务端", 1: "芒果用户端", 2: "芒果执行端"}


class ClientNameEnum(BaseEnum):
    """
    端名称
    """
    DRIVER = '芒果执行器'
    SERVER = '芒果服务器'
    WEB = '芒果用户端'
    PLATFORM_CHINESE = '芒果测试平台'
    PLATFORM_ENGLISH = 'MangoTestPlatform'

    @classmethod
    def obj(cls):
        return {'DRIVER': "芒果执行器", 'SERVER': "芒果服务器", 'WEB': "芒果用户端"}


class SocketEnum(BaseEnum):
    WEB_PATH = '/web/socket'
    CLIENT_PATH = '/client/socket'
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
    PYTEST_GIT_URL = 'git的请求url示例>https://{username}:{password}@gitee.com/mao-peng/MangoPytest.git'
    PYTEST_ACT = 'abstract'
    PYTEST_TESTCASE = 'test_case'
    PYTEST_TOOLS = 'scripts'
    PYTEST_UPLOAD = 'upload'

    @classmethod
    def obj(cls):
        return {
            'SYSTEM_DOMAIN_NAME': None,
            'SYSTEM_SEND_USER': None,
            'SYSTEM_EMAIL_HOST': None,
            'SYSTEM_STAMP_KET': None,
            'API_TIMEOUT': 15,
            'PYTEST_GIT_URL': None,
            'PYTEST_ACT': 'abstract',
            'PYTEST_TESTCASE': 'test_case',
            'PYTEST_TOOLS': 'scripts',
            'PYTEST_UPLOAD': 'upload',
        }

    @classmethod
    def get_cache_value(cls, key):
        from src.auto_test.auto_system.models import CacheData
        return CacheData.objects.get(key=key.value).value

class CacheDataKey2Enum(BaseEnum):
    """缓存KEY的名称，不在系统设置页面展示"""
    SELECT_VALUE = 'select_value'
    ASS_SELECT_VALUE = 'ass_select_value'

    @classmethod
    def obj(cls):
        return {'DOMAIN_NAME': "本系统的URL地址"}
