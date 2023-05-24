# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: api用例执行类
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏

import asyncio

from auto_api.api_tools.async_http_client import AsyncHttpClient


async def main():
    url = 'https://httpbin.org/get'
    params = {'name': 'Alice'}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    # 发送GET请求
    response = await AsyncHttpClient.get(url, params=params, headers=headers)
    print(response)
    url = 'https://httpbin.org/post'
    data = {'name': 'Alice'}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    # 发送POST请求
    response = await AsyncHttpClient.post(url, data=data, headers=headers)
    print(response)


if __name__ == '__main__':
    asyncio.run(main())
