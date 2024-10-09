# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-08-03 16:45
# @Author : 毛鹏
import asyncio
import multiprocessing

import aiohttp
import psutil
import time

URL = ""


class Perf:
    def __init__(self, total_requests):
        self.total_requests = total_requests
        cpu_count = psutil.cpu_count(logical=False)
        self.process_count = min(self.total_requests, cpu_count)
        self.batch_size = self.total_requests // self.process_count
        self.process_pool = multiprocessing.Pool(self.process_count)

    async def make_request(self, session):
        async with session.get(URL) as response:
            return 1 if response.status == 200 else 0

    async def main(self, total_requests):
        async with aiohttp.ClientSession() as session:
            tasks = [asyncio.ensure_future(self.make_request(session)) for i in range(total_requests)]
            success_count = 0
            for coro in asyncio.as_completed(tasks):
                success_count += await coro
            return success_count

    def batch_request(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = []
        for i in range(self.process_count):
            start = (i * self.batch_size)
            end = start + self.batch_size if i < self.process_count - 1 else self.total_requests
            results.append(loop.run_until_complete(self.main(end - start)))
        self.process_pool.close()
        self.process_pool.join()
        return sum(results)
