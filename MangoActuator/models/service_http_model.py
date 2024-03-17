# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-09-28 16:45
# @Author : 毛鹏
from typing import Any

from pydantic import BaseModel


def singleton(cls):
    """
    单例模式
    @param cls:类对象
    @return:
    """
    _instance = {}

    def _singleton(*args, **kwargs):
        if cls not in _instance:
            _instance[cls] = cls(*args, **kwargs)
        return _instance[cls]

    return _singleton


@singleton
class ServiceModel(BaseModel):
    window: Any
    socket: Any


@singleton
class LoginModel(BaseModel):
    ip: str
    port: str
    username: str
    password: str
    user_id: int | None = None
    token: str | None = None
    nickname: str | None = None


if __name__ == '__main__':
    from threading import Thread

    Thread(target=LoginModel(ip='120.0.0.1', port='8000', nickname='1', username='122', user_id='1', token='1'))
    # r = LoginModel(ip='120.0.0.1', port='8000', nickname='1', username='122', user_id='1', token='1')
    # print(r.json())
    print(LoginModel().json())
