# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description:
# @Time   : 2023-04-29 11:19
# @Author : 毛鹏

import concurrent.futures
import logging
import traceback

from django.dispatch import Signal

from PyAutoTest.auto_test.auto_system.service.socket_link.server_interface_reflection.api_consumer import APIConsumer
from PyAutoTest.auto_test.auto_system.service.socket_link.server_interface_reflection.perf_consumer import PerfConsumer
from PyAutoTest.auto_test.auto_system.service.socket_link.server_interface_reflection.system_consumer import \
    SystemConsumer
from PyAutoTest.auto_test.auto_system.service.socket_link.server_interface_reflection.ui_consumer import UIConsumer
from PyAutoTest.models.socket_model import QueueModel
from PyAutoTest.settings.settings import DEBUG
from PyAutoTest.tools.decorator.singleton import singleton

log = logging.getLogger('system')


@singleton
class ServerInterfaceReflection(APIConsumer, SystemConsumer, UIConsumer, PerfConsumer):

    def __init__(self):
        self.executor = concurrent.futures.ThreadPoolExecutor(10)
        self.server_data_received = Signal()
        self.server_data_received.connect(self.data_received_handler)

    def data_received_handler(self, sender, **kwargs):
        if sender == "websocket":
            data = kwargs.get('data')
            if isinstance(data, QueueModel):
                if DEBUG:
                    log.info(f"开始处理接收的消息：{data.model_dump_json()}")
                future = self.executor.submit(getattr(self, data.func_name), data.func_args)
                future.add_done_callback(self.handle_task_result)  # 添加任务完成后的回调函数
            else:
                log.error(f'服务器传递数据错误，请联系管理员查询服务器数据！数据：{data}')

    def handle_task_result(self, future):
        try:
            result = future.result()  # 获取任务执行结果
            # 处理任务执行结果
        except Exception as e:
            traceback.print_exc()  # 打印异常追踪信息
            log.error(f"任务执行出现异常：{e}")
