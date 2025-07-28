# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 封装请求
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏
import json
import time

# from aiohttp import ClientSession
# from aiohttp.client_reqrep import ClientResponse
#
#
# class HTTPRequest:
#
#     @classmethod
#     async def http_get(cls,
#                        session: ClientSession,
#                        url: str,
#                        headers: str) -> tuple[ClientResponse, float]:
#         headers = json.loads(headers)
#         s = time.time()
#         response = await session.get(url, headers=headers)
#         response_time = time.time() - s
#         return response, response_time
#
#     @classmethod
#     async def http_post(cls,
#                         session: ClientSession,
#                         url: str,
#                         headers: str,
#                         data=None) -> tuple[ClientResponse, float]:
#         headers = json.loads(headers)
#         s = time.time()
#         response = await session.post(url, data=data, headers=headers)
#         response_time = time.time() - s
#         return response, response_time
#
#     @classmethod
#     async def http_delete(cls,
#                           session: ClientSession,
#                           url: str,
#                           headers: str,
#                           params=None) -> tuple[ClientResponse, float]:
#         headers = json.loads(headers)
#         s = time.time()
#         response = await session.delete(url, params=params, headers=headers)
#         response_time = time.time() - s
#         return response, response_time
#
#     @classmethod
#     async def http_put(cls,
#                        session: ClientSession,
#                        url: str,
#                        headers: str,
#                        data=None) -> tuple[ClientResponse, float]:
#         headers = json.loads(headers)
#         s = time.time()
#         response = await session.put(url, data=data, headers=headers)
#         response_time = time.time() - s
#         return response, response_time
