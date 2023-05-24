# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 封装请求
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏
import aiohttp


class AsyncHttpClient:
    @classmethod
    async def get(cls, url, params=None, headers=None):
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                return await response.json()

    @classmethod
    async def post(cls, url, data=None, headers=None):
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, headers=headers) as response:
                return await response.json()

    @classmethod
    async def delete(cls, url, params=None, headers=None):
        async with aiohttp.ClientSession() as session:
            async with session.delete(url, params=params, headers=headers) as response:
                return await response.json()

    @classmethod
    async def put(cls, url, data=None, headers=None):
        async with aiohttp.ClientSession() as session:
            async with session.put(url, data=data, headers=headers) as response:
                return await response.json()
