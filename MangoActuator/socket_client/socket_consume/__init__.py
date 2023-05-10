# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/5/10 11:34
# @Author : 毛鹏

import time

from socket_client.queue_ import qu
from socket_client.socket_consume.consume_ui import ConsumeUI


def consume():
    while True:
        data = qu.get()
        for key, value in data.items():
            ConsumeDistribute().start_up(key, value)
        time.sleep(1)
        qu.task_done()


class ConsumeDistribute(ConsumeUI):

    def start_up(self, func, *args, **kwargs):
        getattr(self, func)(*args, **kwargs)
