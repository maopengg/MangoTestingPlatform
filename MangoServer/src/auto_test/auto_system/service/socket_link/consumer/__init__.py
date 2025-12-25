# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-04-29 11:19
# @Author : 毛鹏

import concurrent.futures
import traceback

from django.dispatch import Signal
from mangotools.decorator import singleton

from src.models.socket_model import QueueModel
from src.tools.log_collector import log
from .api import APIConsumer
from .perf import PerfConsumer
from .pytest import PytestConsumer
from .system import SystemConsumer
from .ui import UIConsumer


@singleton
class ServerInterfaceReflection(APIConsumer, SystemConsumer, UIConsumer, PerfConsumer, PytestConsumer):

    def __init__(self):
        self.executor = concurrent.futures.ThreadPoolExecutor(5)
        self.server_data_received = Signal()
        self.server_data_received.connect(self.data_received_handler)

    def data_received_handler(self, sender, **kwargs):
        if sender == "websocket":
            data = kwargs.get('data')
            if isinstance(data, QueueModel):
                log.system.debug(f"消费者开始处理接收的消息：{data.model_dump_json()}")
                future = self.executor.submit(getattr(self, data.func_name), data.func_args)
                future.add_done_callback(self.handle_task_result)
            else:
                log.system.error(f'服务器传递数据错误，请联系管理员查询服务器数据！数据：{data}')

    def handle_task_result(self, future):
        try:
            result = future.result()
        except Exception as e:
            traceback.print_exc()
            log.system.error(f"任务执行出现异常：{e}")
