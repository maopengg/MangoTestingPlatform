# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-26 10:37
# @Author : 毛鹏
import asyncio
import time

import aiohttp


async def index():
    urls = [
        'http://www.example.com/api/1',
        'http://www.example.com/api/2',
        'http://www.example.com/api/3',
        # ...
    ]
    async with aiohttp.ClientSession() as session:
        tasks = [fetch(session, url) for url in urls]
        results = await asyncio.gather(*tasks)
        return results


async def fetch(session, url):
    start_time = time.time()
    async with session.get(url) as response:
        end_time = time.time()
        response_time = end_time - start_time
        print(response.json())
        return {
            'url': url,
            'response_time': response_time
        }


asyncio.run(index())