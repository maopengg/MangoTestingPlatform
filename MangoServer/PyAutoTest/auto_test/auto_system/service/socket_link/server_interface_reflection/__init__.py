# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description:
# @Time   : 2023-04-29 11:19
# @Author : 毛鹏

import concurrent.futures
import logging
import threading
import time
from queue import Queue

from PyAutoTest.auto_test.auto_system.service.socket_link.server_interface_reflection.api_consumer import APIConsumer
from PyAutoTest.auto_test.auto_system.service.socket_link.server_interface_reflection.perf_consumer import PerfConsumer
from PyAutoTest.auto_test.auto_system.service.socket_link.server_interface_reflection.system_consumer import \
    SystemConsumer
from PyAutoTest.auto_test.auto_system.service.socket_link.server_interface_reflection.ui_consumer import UIConsumer
from PyAutoTest.models.system_data_model import QueueModel
from PyAutoTest.utils.other_utils.decorator import singleton

log = logging.getLogger('system')

queue = Queue()


@singleton
class ServerInterfaceReflection(APIConsumer, SystemConsumer, UIConsumer, PerfConsumer):

    def __init__(self):
        self.executor = concurrent.futures.ThreadPoolExecutor(5)

    # def __new__(cls, *args, **kwargs):
    #     if cls._instance is None:
    #         cls._instance = super().__new__(cls)
    #     return cls._instance
    def start_up(self, func, data):
        getattr(self, func)(data)

    def loop_function(self):
        while True:
            data = queue.get()
            if isinstance(data, QueueModel):
                log.info(f"开始处理接收的消息：{data.json()}")
                self.executor.submit(self.start_up(data.func_name, data.func_args))
            else:
                log.error(f'服务器传递数据错误，请联系管理员查询服务器数据！数据：{data}')
            time.sleep(2)

    def while_get_data(self):
        thread = threading.Thread(target=self.loop_function, args={})
        thread.daemon = True
        thread.start()
