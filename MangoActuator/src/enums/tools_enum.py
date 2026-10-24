# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-12-08 9:50
# @Author : 毛鹏

from src.enums import BaseEnum


class MessageEnum(BaseEnum):
    """状态枚举"""
    BOTTOM = 0
    REAL_TIME = 1
    NOTIFICATION = 2
    WS_LINK = 3
    CASE_NAME = 4
    EXECUTION_STATE = 5

    @classmethod
    def obj(cls):
        return {0: "底栏", 1: "首页实时日志", 2: '通知', 3: 'ws链接状态', 4: '用例名称',
                5: '执行状态'}


class CacheKeyEnum(BaseEnum):
    """参数"""
    HOST = 'host'
    WS = 'ws'
    PROXY_URL = 'proxy_url'

    REMEMBER_USERNAME = 'remember_username'
    USERNAME = 'username'
    REMEMBER_PASSWORD = 'remember_password'
    PASSWORD = 'password'

    IS_OPEN = 'is_open'

    WEB_MAX = 'web_max'
    WEB_RECORDING = 'web_recording'
    WEB_PARALLEL = 'web_parallel'
    UI_QUEUE_SIZE = 'ui_queue_size'
    WEB_TYPE = 'web_type'
    WEB_H5 = 'web_h5'
    WEB_PATH = 'web_path'
    WEB_STATIC_CACHE_ENABLED = 'web_static_cache_enabled'
    WEB_STATIC_CACHE_PATH = 'web_static_cache_path'
    WEB_STEP_SCREENSHOT = 'web_step_screenshot'
    WEB_HEADERS = 'web_headers'
    WEB_DEFAULT = 'web_default'

    AND_EQUIPMENT = 'and_equipment'

    IOS_APPIUM_URL = 'ios_appium_url'
    IOS_UDID = 'ios_udid'
    IOS_DEVICE_NAME = 'ios_device_name'
    IOS_PLATFORM_VERSION = 'ios_platform_version'
    IOS_XCODE_ORG_ID = 'ios_xcode_org_id'
    IOS_WDA_BUNDLE_ID = 'ios_wda_bundle_id'

    WIN_PATH = 'win_path'
    WIN_TITLE = 'win_title'

    PYTEST_PARALLEL = 'pytest_parallel'
    PYTEST_QUEUE_SIZE = 'pytest_queue_size'

    @classmethod
    def obj(cls):
        from mangotools.enums import CacheValueTypeEnum
        return {
            'is_open': CacheValueTypeEnum.BOOL,
            'web_max': CacheValueTypeEnum.BOOL, 'web_headers': CacheValueTypeEnum.BOOL,
            'web_recording': CacheValueTypeEnum.BOOL, 'web_step_screenshot': CacheValueTypeEnum.BOOL,
            'web_static_cache_enabled': CacheValueTypeEnum.BOOL,
            'web_parallel': CacheValueTypeEnum.INT,
            'ui_queue_size': CacheValueTypeEnum.INT,
            'web_type': CacheValueTypeEnum.INT,
            'web_default': CacheValueTypeEnum.BOOL,
            'pytest_parallel': CacheValueTypeEnum.INT,
            'pytest_queue_size': CacheValueTypeEnum.INT,
        }
