# -*- coding: utf-8 -*-
# @Project: 芒果测试平台# @Description:
# @Time   : 2023/5/10 11:34
# @Author : 毛鹏
import asyncio
import json
import traceback

from mangokit import singleton

from src.consumer.api import API
from src.consumer.perf import Perf
from src.consumer.tools import Tools
from src.consumer.ui import UI
from src.models.socket_model import QueueModel
from src.models.user_model import UserModel
from src.tools.log_collector import log


@singleton
class SocketConsumer(UI, API, Perf, Tools):
    queue = asyncio.Queue()

    def __init__(self, parent=None, debug: bool = False):
        self.parent = parent
        if not debug:
            self.parent.loop.create_task(self.consumer())
        else:
            settings.IS_DEBUG = debug
            log.set_debug(settings.IS_DEBUG)

    @classmethod
    async def add_task(cls, task):
        await cls.queue.put(task)

    async def consumer(self):
        while True:
            if not self.queue.empty():
                data: QueueModel = await self.queue.get()
                task = self.parent.loop.create_task(getattr(self, data.func_name)(data.func_args))
                task.add_done_callback(self.handle_task_result)
            await asyncio.sleep(0.2)

    @classmethod
    def handle_task_result(cls, task):
        try:
            result = task.result()
        except Exception as e:
            traceback.print_exc()
            log.error(f"反射任务执行出现异常：{e}")

    async def test(self):
        from src.tools import project_dir
        from src.consumer.ui import UI
        with open(fr'{project_dir.root_path()}tests\user_config.json', 'r', encoding='utf-8') as f:
            out = json.load(f)
            UserModel(**out)
        with open(fr'{project_dir.root_path()}\test.json', 'r', encoding='utf-8') as f:
            out = json.load(f)
            if out.get('func_name'):
                await getattr(self, out['func_name'])(out['func_args'])
            else:
                await self.u_case(out)
        while True:
            await asyncio.sleep(1)


class Test:

    def __init__(self):
        from mangokit import Mango
        self.loop = Mango.t()

    def set_tips_info(self, value):
        print(value)


if __name__ == '__main__':
    from src.settings import settings
    from src.network.http import HTTP

    settings.IP = '121.37.174.56'
    settings.PORT = 8000
    HTTP.api.public.set_host(settings.IP, settings.PORT)
    r = SocketConsumer(Test())
    asyncio.run(r.test())
