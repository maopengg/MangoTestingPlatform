# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-04-24 23:39
# @Author : 毛鹏
from src.tools.desktop.signal_send import SignalSend


def case_signal(ago: str | None, after: str | None = None):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if ago:
                SignalSend.notice_signal_c(ago)
            data = func(*args, **kwargs)
            if after:
                SignalSend.notice_signal_c(after)
            return data

        return wrapper

    return decorator
