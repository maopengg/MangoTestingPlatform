# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-08-29 10:23
# @Author : 毛鹏

from cachetools import LRUCache


class CacheTool:
    """ 内存缓存 """
    _cache: LRUCache = LRUCache(maxsize=500)

    @classmethod
    def get_cache(cls, key: str) -> any:
        """
        得到缓存key的value
        @param key: key
        @return: 任意
        """
        return cls._cache.get(key)

    @classmethod
    def set_cache(cls, key: str, value: any) -> None:
        """
        设置一个内容到缓存
        @param key: key
        @param value: value
        @return: None
        """
        cls._cache[key] = value

    @classmethod
    def delete_cache(cls, key: str) -> None:
        """
        删除一个缓存
        @param key: key
        @return: None
        """
        if key in cls._cache:
            del cls._cache[key]

    @classmethod
    def clear_cache(cls) -> None:
        """
        清理所有缓存
        @return: None
        """
        cls._cache.clear()

    @classmethod
    def has_cache(cls, key: str) -> bool:
        """
        判断缓存是否存在
        @param key: key
        @return: ture | false
        """
        return key in cls._cache

    @classmethod
    def get_all(cls, ) -> dict:
        return {k: v for k, v in cls._cache.items()}
