from src.common.enums.base import BaseEnum


class SystemConfigManagementLevelEnum(BaseEnum):
    """系统配置在管理页面中的可见性和修改风险等级。"""

    INTERNAL = (1, "系统内部")
    CAUTION = (2, "谨慎修改")
    STANDARD = (3, "普通配置")


class CacheDataKeyEnum(BaseEnum):
    """缓存KEY的名称"""
    SYSTEM_DOMAIN_NAME = '本系统的URL地址'
    SYSTEM_SEND_USER = '邮箱发送人'
    SYSTEM_EMAIL_HOST = '邮箱域名'
    SYSTEM_STAMP_KET = '邮箱的stamp_key'
    API_TIMEOUT = 'API请求超时时间'

    @classmethod
    def obj(cls):
        return {
            'SYSTEM_DOMAIN_NAME': None,
            'SYSTEM_SEND_USER': None,
            'SYSTEM_EMAIL_HOST': None,
            'SYSTEM_STAMP_KET': None,
            'API_TIMEOUT': 120,
        }

    @classmethod
    def get_cache_value(cls, key):
        from src.apps.system.services.system_config import SystemConfigService
        return SystemConfigService.get(key.name)


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
    TEST_DATA_SELECT_VALUE = 'test_data_select_value'

    @classmethod
    def obj(cls):
        return {'DOMAIN_NAME': "本系统的URL地址"}
