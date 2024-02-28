# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-04-29 11:23
# @Author : 毛鹏
from enum import Enum


class BaseEnum(Enum):
    """基础枚举类，提供通用的三个方法"""

    @classmethod
    def get_option(cls) -> list:
        return [{'key': key, 'title': value} for key, value in cls.obj().items()]

    @classmethod
    def get_value_list(cls) -> list:
        return [value for key, value in cls.obj().items()]

    @classmethod
    def get_key_list(cls) -> list:
        return [key for key, value in cls.obj().items()]

    @classmethod
    def get_value(cls, key: int):
        return cls.obj().get(key)

    @classmethod
    def get_key(cls, value):
        all_values = cls.obj().values()

        # 判断目标值是否存在于字典的值列表中
        if value in all_values:
            # 如果存在，则使用keys()函数获取该值对应的键列表
            keys_with_target_value = [k for k, v in cls.obj().items() if v == value]

            for key in keys_with_target_value:
                return key
