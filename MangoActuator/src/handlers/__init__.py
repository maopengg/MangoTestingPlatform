# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023/5/10 11:34
# @Author : 毛鹏
import asyncio
import json
import traceback

from src.handlers.api_consumer import APIConsumer
from src.handlers.perf_consumer import PerfConsumer
from src.handlers.tools_consumer import ToolsConsumer
from src.handlers.ui_consumer import UIConsumer
from src.models.network_model import QueueModel
from src.tools.log_collector import log


class InterfaceMethodReflection(UIConsumer, APIConsumer, PerfConsumer, ToolsConsumer):

    def __init__(self, debug: bool = False):
        self.queue = asyncio.Queue()
        if not debug:
            self.loop = asyncio.get_event_loop()
            self.loop.create_task(self.consumer())
        else:
            settings.IS_DEBUG = debug

    async def consumer(self):
        while True:
            if not self.queue.empty():
                data: QueueModel = await self.queue.get()
                task = self.loop.create_task(getattr(self, data.func_name)(data.func_args))
                task.add_done_callback(self.handle_task_result)
            await asyncio.sleep(0.2)

    @classmethod
    def handle_task_result(cls, task):
        try:
            result = task.result()  # 获取任务执行结果
            # 处理任务执行结果
        except Exception as e:
            traceback.print_exc()  # 打印异常追踪信息
            log.error(f"反射任务执行出现异常：{e}")

    async def test(self):
        from src.tools import InitPath
        with open(fr'{InitPath.logs_dir}\test.json', 'r', encoding='utf-8') as f:
            out = json.load(f)
            await getattr(self, out['func_name'])(out['func_args'])
        while True:
            await asyncio.sleep(1)


if __name__ == '__main__':
    from src.settings import settings

    settings.IP = '127.0.0.1'
    settings.PORT = 8000
    r = InterfaceMethodReflection(True)
    asyncio.run(r.test())
