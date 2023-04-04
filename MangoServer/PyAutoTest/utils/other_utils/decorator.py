# -*- coding: utf-8 -*-
# @Project: auto_test
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


if __name__ == '__main__':
    work()
