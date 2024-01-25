# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023/3/23 11:25
# @Author : 毛鹏
import logging

from PyAutoTest.tools.cache_utils.redis_base import RedisBase

log = logging.getLogger('system')


class SystemConsumer:

    @classmethod
    def t_set_operation_options(cls, data: list[dict]):
        redis = RedisBase('default')
        for i in data:
            for key, value in i.items():
                redis.set_key(key, value)
