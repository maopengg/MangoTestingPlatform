# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 统计函数运行时间
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏

import time


def decorator(func):
    def inner():
        # 获取时间距离1970-1-1 0:0:1的时间差
        begin = time.time()
        func()
        result = time.time() - begin
        print(f'函数执行完成耗时：{result}')

    return inner


@decorator
def work():
    for i in range(10000):
        print(i)


def convert_args(set_type, set_=None):
    """
    转换类型装饰器
    @param set_:
    @param set_type:
    @return:
    """

    def decorator(func):
        async def wrapper(self, data):
            if set_ == 'list':
                data = [set_type(**i) for i in data]
            elif set_ == 'str':
                data = data
            else:
                data = set_type(data)
            return await func(self, data)

        return wrapper

    return decorator


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


if __name__ == '__main__':
    work()
