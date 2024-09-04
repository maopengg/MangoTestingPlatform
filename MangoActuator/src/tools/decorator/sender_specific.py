# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-01-30 13:19
# @Author : 毛鹏
from blinker import signal

# 创建一个名为 'custom_signal' 的信号
from src.models.ui_model import WEBConfigModel

custom_signal = signal('custom_signal')


# 定义装饰器，用于指定处理函数只在特定的发送者下被触发
def sender_specific(sender_name):
    def decorator(func):
        def wrapper(sender, **kwargs):
            if sender == sender_name:
                return func(sender, WEBConfigModel(**kwargs.get('data')))

        return wrapper

    return decorator
