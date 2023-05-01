# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-29 11:19
# @Author : 毛鹏
from socket_client.api_collection.uiauto_api import UiAutoApi
from socket_client.api_collection.apiauto_api import ApiAutoApi
from socket_client.api_collection.command_api import ExternalAPI
from socket_client.server_enum.test_enum import ApiTestEnum


class Collection(ApiAutoApi, UiAutoApi, ExternalAPI):

    def start_up(self, func, *args, **kwargs):
        getattr(self, func)(*args, **kwargs)


collection = Collection()
if __name__ == '__main__':
    collection.start_up(ApiTestEnum.run_debug_batch_case.value, 'haha')
