# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-29 11:19
# @Author : 毛鹏
from queue import Queue
from typing import Optional

from socket_client.queue_ import qu
from socket_client.server_enum.test_enum import ApiTestEnum
from socket_client.socket_product.apiauto_api import ApiAutoApi
from socket_client.socket_product.command_api import ExternalAPI
from socket_client.socket_product.product_ui import UiAutoApi


class Collection(ApiAutoApi, UiAutoApi, ExternalAPI):

    def __init__(self):
        super().__init__()
        self.qu: Optional[Queue] = qu

    def start_up(self, func, *args, **kwargs):
        getattr(self, func)(*args, **kwargs)


collection = Collection()
if __name__ == '__main__':
    collection.start_up(ApiTestEnum.run_debug_batch_case.value, 'haha')
