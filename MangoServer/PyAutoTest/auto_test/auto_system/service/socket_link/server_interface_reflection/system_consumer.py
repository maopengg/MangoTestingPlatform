# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023/3/23 11:25
# @Author : 毛鹏

from PyAutoTest.auto_test.auto_system.models import CacheData
from PyAutoTest.auto_test.auto_system.views.cache_data import CacheDataCRUD
from PyAutoTest.enums.system_enum import CacheValueTypeEnum


class SystemConsumer:

    @classmethod
    def t_set_operation_options(cls, data: list[dict]):
        # redis = RedisBase('default')
        for i in data:
            for key, value in i.items():
                try:
                    cache_data = CacheData.objects.get(key=key)
                except CacheData.DoesNotExist:
                    CacheDataCRUD.inside_post({
                        'describe': key,
                        'key': key,
                        'value': value,
                        'value_type': CacheValueTypeEnum.DICT.value,
                    })
                except CacheData.MultipleObjectsReturned:
                    cache_data_list = CacheData.objects.filter(key=key)
                    for cache_data in cache_data_list:
                        cache_data.delete()
                    CacheDataCRUD.inside_post({
                        'describe': key,
                        'key': key,
                        'value': value,
                        'value_type': CacheValueTypeEnum.DICT.value,
                    })
                else:
                    CacheDataCRUD.inside_put(cache_data.id, {
                        'describe': key,
                        'key': key,
                        'value': value,
                        'value_type': CacheValueTypeEnum.DICT.value,
                    })
