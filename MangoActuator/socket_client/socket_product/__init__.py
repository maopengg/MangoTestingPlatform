# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-29 11:19
# @Author : 毛鹏
import multiprocessing

from socket_client.socket_product.apiauto_api import ApiAutoApi
from socket_client.socket_product.command_api import ExternalAPI
from socket_client.socket_product.product_ui import UiAutoApi
from utils.decorator.singleton import singleton


@singleton
class Collection(ApiAutoApi, UiAutoApi, ExternalAPI):

    def __init__(self, qu: multiprocessing.Queue):
        super().__init__()
        self.qu = qu

    def start_up(self, func, *args, **kwargs):
        getattr(self, func)(*args, **kwargs)
