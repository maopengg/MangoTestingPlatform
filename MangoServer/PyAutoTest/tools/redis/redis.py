# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: redis缓存封装
# @Time   : 2022-11-22 8:34
# @Author : 毛鹏
import datetime
import json

from django.core.cache import cache


class Cache:
    @staticmethod
    def exist_cache(key):
        """
        判断缓存数据是否存在1
        :param key: 唯一标识
        :return: 存在结果
        """
        is_exist = False
        if key in cache:
            is_exist = True

        return is_exist

    @staticmethod
    def clear_cache(key):
        """
        清除缓存数据
        :param key：唯一标识
        """
        if key in cache:
            cache.delete(key)

    @staticmethod
    def clear_pattern_cache(fuzzy_key):
        """
        清除缓存数据
        :param fuzzy_key：模糊标识
        :return:
        """
        cache.delete_pattern("*%s*" % fuzzy_key)

    @staticmethod
    def write_data_to_cache(key, value, expire=None):
        """
        将数据直接写入缓存
        :param key：唯一标识
        :param value：写入的数据
        :param expire：失效时间（单位为秒），默认为不失效
        """
        cache.set(key, value, timeout=expire)

    @staticmethod
    def write_json_to_cache(key, value, expire=None):
        """
        将数据转为json格式写入缓存
        :param key：唯一标识
        :param value：写入的数据
        :param expire：失效时间（单位为秒），默认为不失效
        """
        cache.set(key, json.dumps(value, cls=CJsonEncoder), timeout=expire)

    @staticmethod
    def write_counter_to_cache(key, step=1, expire=None):
        """
        计数器写入缓存
        :param key：唯一标识
        :param step：计数器每次递增的值（支持负数进行递减），默认每次递增1
        :param expire：失效时间（单位为秒），默认为不失效
        """
        if key in cache:
            cache.incr(key, step)
        else:
            cache.set(key, 1, expire)

    @staticmethod
    def read_pattern_data_from_cache(fuzzy_key):
        """
        读取缓存
        :param fuzzy_key：模糊标识
        :return：缓存数据
        """
        keys = cache.keys("*%s*" % fuzzy_key)
        data = []
        for key in keys:
            data.append({
                'key': key,
                'value': cache.get(key)
            })
        return data

    @staticmethod
    def read_data_from_cache(key) -> str:
        """
        直接读取缓存
        :param key：唯一标识
        :return：缓存数据
        """
        if key in cache:
            data = cache.get(key)
        else:
            data = None
        return data

    @staticmethod
    def read_json_from_cache(key):
        """
        读取json格式缓存
        :param key：唯一标识
        :return：缓存进行json解析后数据
        """
        if key in cache:
            data = json.loads(cache.get(key))
        else:
            data = None
        return data


class CJsonEncoder(json.JSONEncoder):
    """
    重写构造json类，遇到日期特殊处理
    """

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, datetime.date):
            return obj.strftime("%Y-%m-%d")
        else:
            return json.JSONEncoder.default(self, obj)


def redis_caches():
    """
    不失效缓存，key为加载此装饰器的函数名
    :param:
    :return:
    """

    def _deco(func):
        def __deco(*args, **kwargs):
            redis_key = func.__name__
            cache_info = Cache().read_data_from_cache(redis_key)
            if not cache_info:
                result = func(*args, **kwargs)
                Cache().write_data_to_cache(redis_key, result)
            else:
                result = cache_info
            return result

        return __deco

    return _deco
