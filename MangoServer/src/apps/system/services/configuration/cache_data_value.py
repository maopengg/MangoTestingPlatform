# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-02-28 17:32
# @Author : 毛鹏
from src.apps.system.services.configuration.system_config import SystemConfigService


class CacheDataValue:

    @classmethod
    def get_cache_value(cls, key: str):
        return SystemConfigService.get(key)
