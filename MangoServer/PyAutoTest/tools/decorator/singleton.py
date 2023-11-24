# -*- coding: utf-8 -*-
# @Project: 单例模式
# @Description: 
# @Time   : 2023/4/26 17:41
# @Author : 毛鹏


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
