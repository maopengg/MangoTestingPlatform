# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-05-10 8:40
# @Author : 毛鹏
import asyncio
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Process
from queue import Queue


def consume(queue: Queue):
    def handle_data(data):
        # 处理data的代码
        print(f"Consumed {data}")

    with ProcessPoolExecutor(max_workers=10) as executor:
        for data in queue:
            if data is None:
                break
            executor.submit(handle_data, data)


async def produce(queue):
    for i in range(10):
        data = i
        queue.put(data)
        await asyncio.sleep(1)
    await queue.put(None)


def start_consumer(queue):
    p = Process(target=consume, args=(queue,))
    p.run()
    p.join()


async def main():
    queue = Queue()
    start_consumer(queue)
    produce_task = asyncio.create_task(produce(queue))
    await asyncio.gather(produce_task)
    queue.put(None)


asyncio.run(main())
