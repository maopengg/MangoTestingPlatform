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
from src.network import HTTP
from src.settings import settings


class LinuxLoop:

    def __init__(self):
        self.loop = Mango.t()

    def set_tips_info(self, value):
        print(value)


async def run():
    loop = LinuxLoop()
    settings.IP = '127.0.0.1'
    settings.PORT = '8000'
    settings.IS_DEBUG = True
    settings.USERNAME = 'admin'
    settings.PASSWORD = '123456'
    HTTP.api.public.set_host(settings.IP, settings.PORT)
    await test_process(loop)
    with open('test.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        await SocketConsumer.add_task(QueueModel(func_name=data.get('func_name'), func_args=data.get('func_args')))
    while True:
        await asyncio.sleep(0.1)


asyncio.run(run())
