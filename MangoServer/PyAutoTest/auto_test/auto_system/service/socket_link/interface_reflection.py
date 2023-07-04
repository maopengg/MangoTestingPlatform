# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-07-04 15:19
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
from PyAutoTest.base_data_model.system_data_model import QueueModel

log = logging.getLogger('system')


class ServerInterfaceReflection(APIConsumer, SystemConsumer, UIConsumer, PerfConsumer):
    _instance = None

    def __init__(self):
        super().__init__()
        self.q = Queue()
        self.executor = concurrent.futures.ThreadPoolExecutor(5)

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def start_up(self, func, *args, **kwargs):
        getattr(self, func)(*args, **kwargs)

    def loop_function(self):
        while True:
            data = self.q.get()
            if isinstance(data, QueueModel):
                log.debug(f"{data.json()}")
                self.executor.submit(self.start_up(data.func_name, data.func_args))
            else:
                log.error(f'服务器传递数据错误，请联系管理员查询服务器数据！数据：{data}')
            time.sleep(2)

    def while_get_data(self):
        thread = threading.Thread(target=self.loop_function)
        thread.daemon = True
        thread.start()
