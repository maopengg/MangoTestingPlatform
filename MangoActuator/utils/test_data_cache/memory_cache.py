# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-05-24 22:35
# @Author : 毛鹏
import asyncio

from aiocache import Cache


class MemoryCache:
    _cache = Cache()

    @classmethod
    async def get(cls, key):
        return await cls._cache.get(key)

    @classmethod
    async def set(cls, key, value, ttl=None):
        await cls._cache.set(key, value, ttl=ttl)

    @classmethod
    async def delete(cls, key):
        await cls._cache.delete(key)

    @classmethod
    async def clear(cls):
        await cls._cache.clear()

    @classmethod
    async def close(cls):
        await cls._cache.close()


mc = MemoryCache()

if __name__ == "__main__":
    async def test_cache():
        await MemoryCache.set("key", "hahaha")
        value = await MemoryCache.get("key")
        print(value)
        await MemoryCache.delete("key")
        value = await MemoryCache.get("key")
        print(value)


    asyncio.run(test_cache())
