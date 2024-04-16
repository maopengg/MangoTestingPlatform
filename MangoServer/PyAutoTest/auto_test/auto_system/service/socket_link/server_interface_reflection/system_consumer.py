# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023/3/23 11:25
# @Author : 毛鹏
import logging

from PyAutoTest.auto_test.auto_system.models import CacheData
from PyAutoTest.auto_test.auto_system.views.cache_data import CacheDataSerializers, CacheDataCRUD
from PyAutoTest.enums.system_enum import CacheValueTypeEnum

log = logging.getLogger('system')


class SystemConsumer:

    @classmethod
    def t_set_operation_options(cls, data: list[dict]):
        # redis = RedisBase('default')
        for i in data:
            for key, value in i.items():
                if not CacheData.objects.filter(key=key):
                    serializer = CacheDataSerializers(data={
                        'describe': key,
                        'key': key,
                        'value': value,
                        'value_type': CacheValueTypeEnum.DICT.value,
                    })
                    if serializer.is_valid():
                        serializer.save()
                    else:
                        log.error(f'执行修改时报错，请检查！数据：{data}, 报错信息：{str(serializer.errors)}')