# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-05-13 22:39
# @Author : 毛鹏
import logging

import _ctypes

from PyAutoTest.auto_test.auto_system.consumers import ChatConsumer
from PyAutoTest.tools.redis.redis_base import RedisBase

log = logging.getLogger('system')


class SocketUserRedis(RedisBase):

    def __init__(self, library='socket'):
        super().__init__(library)

    def set_user_conn_obj(self, user, key, value):
        self.set_hset(name=user, key=key, value=id(value))

    def get_user_web_obj(self, user) -> ChatConsumer | None:
        """ 获取web端对象"""
        obj_id = self.get_hgetall(name=user).get('web_obj')
        for obj in globals().values():
            if isinstance(obj, ChatConsumer) and id(obj) == int(obj_id):
                return obj
        return None
        # return _ctypes.PyObj_FromPtr(int(obj_id)) if obj_id else None

    def get_user_client_obj(self, user) -> ChatConsumer:
        """获取执行端对象"""
        obj_id = self.get_hgetall(name=user).get('client_obj')
        return _ctypes.PyObj_FromPtr(int(obj_id)) if obj_id else None

    def delete_all(self, user):
        """web端断开则删除所有"""
        self.delete(user)

    def delete_key(self, user, key):
        """删除redis中的key"""
        self.hdel(user, key)

    def all_delete(self):
        self.delete_all_()

    def get_all_user(self):
        result = []
        for key in self.all_keys():
            data = self.get_hget(key, 'client_obj')
            if data:
                result.append(key)
        return result
