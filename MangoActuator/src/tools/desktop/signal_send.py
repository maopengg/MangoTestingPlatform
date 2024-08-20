# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-04-24 14:28
# @Author : 毛鹏
from blinker import signal

from src.enums.tools_enum import SignalTypeEnum


class SignalSend:
    custom = signal('custom_signal')
    notice = signal('notice_signal')

    @classmethod
    def notice_signal_c(cls, msg: str):
        cls.notice.send(SignalTypeEnum.C, data=msg)

    @classmethod
    def notice_signal_a(cls, msg: str):
        cls.notice.send(SignalTypeEnum.A, data=msg)

    @classmethod
    def func_signal(cls, func: str, data):
        cls.custom.send(func, data=data)
