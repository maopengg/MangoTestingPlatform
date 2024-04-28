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
from tools.desktop.signal_send import SignalSend
from tools.log_collector import log


class InterfaceMethodReflection(UIConsumer, APIConsumer, PerfConsumer, ToolsConsumer):

    def __init__(self):
        # custom_signal.disconnect(self.consumer)
        SignalSend.custom.connect(self.consumer)

    def consumer(self, sender, data: dict):
        if sender == "break":
            os._exit(0)
        task = asyncio.create_task(getattr(self, sender)(data))
        task.add_done_callback(self.handle_task_result)

    @classmethod
    def handle_task_result(cls, task):
        try:
            result = task.result()  # 获取任务执行结果
            # 处理任务执行结果
        except Exception as e:
            traceback.print_exc()  # 打印异常追踪信息
            log.error(f"反射任务执行出现异常：{e}")

    async def test(self):
        with open(r'..\..\..\test.json', 'r', encoding='utf-8') as f:
            out = json.load(f)
            for i in out:
                data = QueueModel(**i)
                await getattr(self, data.func_name)(data.func_args)


r = InterfaceMethodReflection()

if __name__ == '__main__':
    asyncio.run(r.test())
    # pass
