# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023/3/23 11:25
# @Author : 毛鹏
import json

from src.auto_test.auto_system.models import CacheData
from src.auto_test.auto_system.views.cache_data import CacheDataCRUD
from src.enums.system_enum import CacheDataKey2Enum
from src.enums.tools_enum import CacheValueTypeEnum


class SystemConsumer:

    @classmethod
    def t_set_operation_options(cls, data: list[dict]):
        data = {
            'describe': CacheDataKey2Enum.SELECT_VALUE.value,
            'key': CacheDataKey2Enum.SELECT_VALUE.value,
            'value': json.dumps(data, ensure_ascii=False),
            'value_type': CacheValueTypeEnum.DICT.value,
        }
        try:
            cache_data = CacheData.objects.get(key=CacheDataKey2Enum.SELECT_VALUE.value)
        except CacheData.DoesNotExist:
            CacheDataCRUD.inside_post(data)
        except CacheData.MultipleObjectsReturned:
            cache_data_list = CacheData.objects.filter(key=CacheDataKey2Enum.SELECT_VALUE.value)
            for cache_data in cache_data_list:
                cache_data.delete()
            CacheDataCRUD.inside_post(data)
        else:
            CacheDataCRUD.inside_put(cache_data.id, data)
