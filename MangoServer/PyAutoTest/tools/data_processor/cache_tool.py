# -*- coding: utf-8 -*-
# @Project: 芒果测试平台# @Description:
# @Time   : 2023-08-29 10:23
# @Author : 毛鹏

from cachetools import LRUCache


class CacheTool:
    """ 内存缓存 """

    def __init__(self):
        self._cache: LRUCache = LRUCache(maxsize=500)

    def get_cache(self, key: str) -> any:
        """
        得到缓存key的value
        @param key: key
        @return: 任意
        """
        return self._cache.get(key)

    def set_cache(self, key: str, value: any) -> None:
        """
        设置一个内容到缓存
        @param key: key
        @param value: value
        @return: None
        """
        self._cache[key] = value

    def delete_cache(self, key: str) -> None:
        """
        删除一个缓存
        @param key: key
        @return: None
        """
        if key in self._cache:
            del self._cache[key]

    def clear_cache(self) -> None:
        """
        清理所有缓存
        @return: None
        """
        self._cache.clear()

    def has_cache(self, key: str) -> bool:
        """
        判断缓存是否存在
        @param key: key
        @return: ture | false
        """
        return key in self._cache

    def get_all(self, ) -> dict:
        return {k: v for k, v in self._cache.items()}
