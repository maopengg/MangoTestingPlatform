# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023/5/10 11:34
# @Author : 毛鹏
import asyncio
import json
import os
import traceback

from models.socket_model import QueueModel
from service.socket_client.api_reflection.api_consumer import APIConsumer
from service.socket_client.api_reflection.perf_consumer import PerfConsumer
from service.socket_client.api_reflection.tools_consumer import ToolsConsumer
from service.socket_client.api_reflection.ui_consumer import UIConsumer
from tools.log_collector import log


class InterfaceMethodReflection(UIConsumer, APIConsumer, PerfConsumer, ToolsConsumer):

    def __init__(self):
        self.queue = asyncio.Queue()
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.consumer())

    async def consumer(self):
        while True:
            if not self.queue.empty():
                data: QueueModel = await self.queue.get()
                if data.func_name == "break":
                    os._exit(0)
                task = self.loop.create_task(getattr(self, data.func_name)(data.func_args))
                task.add_done_callback(self.handle_task_result)
            else:
                await asyncio.sleep(0.1)

    @classmethod
    def handle_task_result(cls, task):
        try:
            result = task.result()  # 获取任务执行结果
            # 处理任务执行结果
        except Exception as e:
            traceback.print_exc()  # 打印异常追踪信息
            log.error(f"反射任务执行出现异常：{e}")

    async def test(self):
        with open(r'test.json', 'r', encoding='utf-8') as f:
            out = json.load(f)
            for i in out:
                await getattr(self, 'u_case')(i)

        while True:
            await asyncio.sleep(1)


r = InterfaceMethodReflection()

if __name__ == '__main__':
    asyncio.run(r.test())

    # pass
