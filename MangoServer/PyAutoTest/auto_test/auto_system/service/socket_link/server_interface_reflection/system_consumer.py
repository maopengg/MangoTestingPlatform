# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023/3/23 11:25
# @Author : 毛鹏
import logging

from PyAutoTest.auto_test.auto_system.views.cache_data import CacheDataCRUD
from PyAutoTest.enums.system_enum import CacheValueTypeEnum

log = logging.getLogger('system')


class SystemConsumer:

    @classmethod
    def t_set_operation_options(cls, data: list[dict]):
        # redis = RedisBase('default')
        for i in data:
            for key, value in i.items():
                CacheDataCRUD().inside_post({
                    'describe': key,
                    'key': key,
                    'value': value,
                    'value_type': CacheValueTypeEnum.DICT.value,
                })
                # redis.set_key(key, value)
