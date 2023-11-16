# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 随机数据封装
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏
import random

import time
from faker import Faker


class RandomNumberData:
    """ 随机的数字类型测试数据 """
    faker = Faker(locale='zh_CN')

    @staticmethod
    def time_random():
        """获取基于当前时间戳的随机五位数"""
        s = int(time.time())
        s = str(s)
        return s[5:len(s)]

    @staticmethod
    def random_0_9() -> int:
        """0-9的随机数"""
        _data = random.randint(0, 9)
        return _data

    @staticmethod
    def random_0_5() -> int:
        """0-9的随机数"""
        _data = random.randint(0, 5)
        return _data

    @staticmethod
    def random_10_99() -> int:
        """10-99的随机数"""
        _data = random.randint(10, 99)
        return _data

    @staticmethod
    def random_100_999() -> int:
        """100-999的随机数"""
        _data = random.randint(100, 999)
        return _data

    @staticmethod
    def random_0_5000() -> int:
        """0-5000的随机数"""
        _data = random.randint(0, 5000)
        return _data

    @staticmethod
    def random_float():
        """小数"""
        return random.random()

    @staticmethod
    def random_two_float():
        """随机两位小数"""
        return round(random.random(), 2)

    @classmethod
    def random_1000_two_float(cls):
        """1000以内的随机两位小数"""
        return cls.random_100_999() + round(random.random(), 2)
