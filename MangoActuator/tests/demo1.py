# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-02-26 20:08
# @Author : 毛鹏
import asyncio
import json

from mangokit.mangos import Mango

from src import test_process
from src.consumer import SocketConsumer
from src.models.socket_model import QueueModel


class LinuxLoop:

    def __init__(self):
        self.loop = Mango.t()

    def set_tips_info(self, value):
        print(value)


async def run():
    loop = LinuxLoop()

    await test_process(loop)
    with open('test.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        await SocketConsumer.add_task(QueueModel(func_name=data.get('func_name'), func_args=data.get('func_args')))
    while True:
        await asyncio.sleep(0.2)


async def run_func():
    from src.models.ui_model import CaseModel
    from src.services.ui.case_flow import CaseFlow
    CaseFlow.parent = LinuxLoop()
    with open('test.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        await CaseFlow.execute_task(CaseModel(**data.get('func_args')))


asyncio.run(run_func())
