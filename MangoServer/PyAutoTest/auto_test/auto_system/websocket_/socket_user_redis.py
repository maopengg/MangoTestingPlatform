# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-05-13 22:39
# @Author : 毛鹏
from PyAutoTest.utils.cache_utils.redis import Cache


class SocketUserRedis(Cache):

    def set_user(self):
        self.write_data_to_cache(key='person:1', value={'user': 18071710220})


if __name__ == '__main__':
    SocketUserRedis().set_user()
