from django.apps import apps
from mangotools.enums import CacheValueTypeEnum

from src.apps.system.enums import CacheDataKey2Enum, SystemConfigManagementLevelEnum
from src.common.logging import log
from src.common.testing import assertion_func_info


class SystemInitializationService:
    @staticmethod
    def initialize() -> dict:
        user_config = apps.get_app_config('auto_user')
        SystemInitializationService.save_cache()
        SystemInitializationService.populate_time_tasks()
        SystemInitializationService.init_ass()
        user_config.new_role()
        user_config.new_user()
        return {
            'system_config': True,
            'time_tasks': True,
            'assertion_cache': True,
            'default_roles': True,
            'default_users': True,
        }

    @staticmethod
    def save_cache():
        try:
            from src.apps.system.services.configuration.system_config import SystemConfigService
            SystemConfigService.sync_registered_configs()
        except Exception as e:
            log.system.error(f'异常提示:{e}, 首次启动项目，请启动完成之后再重启一次！')
            raise

    @staticmethod
    def populate_time_tasks():
        try:
            from src.apps.task_center.services.scheduling.default_time_tasks import DefaultTimeTaskService

            DefaultTimeTaskService.populate()
        except Exception as e:
            log.system.error(f'初始化定时任务配置失败: {e}')
            raise

    @staticmethod
    def init_ass():
        try:
            import json

            from src.apps.system.models import CacheData
            from src.apps.system.services.configuration.system_config import SystemConfigService
            from src.apps.system.services.configuration.cache_data import CacheDataService

            data = {
                'describe': CacheDataKey2Enum.ASS_SELECT_VALUE.value,
                'key': CacheDataKey2Enum.ASS_SELECT_VALUE.value,
                'value': json.dumps(assertion_func_info, ensure_ascii=False),
                'value_type': CacheValueTypeEnum.DICT.value,
                'group': 'internal',
                'management_level': SystemConfigManagementLevelEnum.INTERNAL.value,
                'is_enabled': True,
            }
            CacheDataService.upsert_unique_key(CacheDataKey2Enum.ASS_SELECT_VALUE.value, data)
            SystemConfigService.invalidate(CacheDataKey2Enum.ASS_SELECT_VALUE.value)
        except Exception as e:
            log.system.error(f'异常提示:{e}, 首次启动项目，请启动完成之后再重启一次！')
            raise
