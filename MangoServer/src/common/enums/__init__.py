# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-04-29 11:23
# @Author : 毛鹏
from enum import Enum


class BaseEnum(Enum):
    """基础枚举类，提供通用的三个方法"""

    @classmethod
    def get_option(cls, k='key', v='title') -> list:
        return [{k: key, v: value} for key, value in cls.obj().items()]  # type: ignore

    @classmethod
    def get_value_list(cls) -> list:
        return [value for key, value in cls.obj().items()]  # type: ignore

    @classmethod
    def get_key_list(cls) -> list:
        return [key for key, value in cls.obj().items()]  # type: ignore

    @classmethod
    def get_value(cls, key: int):
        return cls.obj().get(key)  # type: ignore

    @classmethod
    def get_key(cls, value):
        all_values = cls.obj().values()  # type: ignore
        if value in all_values:
            keys_with_target_value = [k for k, v in cls.obj().items() if v == value]  # type: ignore
            for key in keys_with_target_value:
                return key

    @classmethod
    def reversal_obj(cls):
        return {v: k for k, v in cls.obj().items()}

    @classmethod
    def choices(cls):
        """返回 Django IntegerField choices 格式"""
        return [(key, label) for key, label in cls.obj().items()]
