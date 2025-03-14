# -*- coding: utf-8 -*-
# @Project: 芒果测试平台# @Description:
# @Time   : 2023/5/10 11:34
# @Author : 毛鹏
import asyncio
import json
import traceback

from src.consumer.api import API
from src.consumer.perf import Perf
from src.consumer.tools import Tools
from src.consumer.ui import UI
from src.models.socket_model import QueueModel
from src.models.user_model import UserModel
from src.settings import settings
from src.tools.log_collector import log


class SocketConsumer(UI, API, Perf, Tools):
    queue = asyncio.Queue()
    parent = None
    running = True

    @classmethod
    async def add_task(cls, task):
        await cls.queue.put(task)

    @classmethod
    async def set_log(cls, debug: bool = False):
        settings.IS_DEBUG = debug
        log.set_debug(settings.IS_DEBUG)

    @classmethod
    async def process_tasks(cls):
        while cls.running:
            if not cls.queue.empty():
                data: QueueModel = await cls.queue.get()
                task = cls.parent.loop.create_task(getattr(cls, data.func_name)(data.func_args))
                task.add_done_callback(cls.handle_task_result)
            else:
                # 当队列为空时，让出控制权，避免阻塞事件循环
                await asyncio.sleep(0.1)

    @classmethod
    def handle_task_result(cls, task):
        try:
            result = task.result()
        except Exception as error:
            traceback.print_exc()
            log.error(f"反射任务执行出现异常：{error}")

    @classmethod
    def stop(cls):
        cls.running = False

    @classmethod
    async def test(cls):
        from src.tools import project_dir
        from src.consumer.ui import UI
        with open(fr'{project_dir.root_path()}tests\user_config.json', 'r', encoding='utf-8') as f:
            out = json.load(f)
            UserModel(**out)
        with open(fr'{project_dir.root_path()}\test.json', 'r', encoding='utf-8') as f:
            out = json.load(f)
            if out.get('func_name'):
                await getattr(cls, out['func_name'])(out['func_args'])
            else:
                await cls.u_case(out)
        while True:
            await asyncio.sleep(1)


class Test:

    def __init__(self):
        from mangokit import Mango
        self.loop = Mango.t()

    def set_tips_info(self, value):
        print(value)


if __name__ == '__main__':
    from src.network.http import HTTP

    settings.IP = '121.37.174.56'
    settings.PORT = 8000
    HTTP.api.public.set_host(settings.IP, settings.PORT)
    SocketConsumer.parent = Test()
    asyncio.run(SocketConsumer.test())
