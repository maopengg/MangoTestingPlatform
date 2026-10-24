# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-04-29 11:23
# @Author : 毛鹏
from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class ComboBoxDataModel:
    """Framework-neutral option model kept for legacy callers of get_select."""

    id: str
    name: str


class BaseEnum(Enum):
    """基础枚举类，提供通用的三个方法"""

    @classmethod
    def get_option(cls, k='key', v='title') -> list:
        return [{k: str(key), v: value} for key, value in cls.obj().items()]  # type: ignore

    @classmethod
    def get_obj(cls) -> dict:
        return cls.obj()  # type: ignore

    @classmethod
    def get_value_list(cls) -> list:
        return [value for key, value in cls.obj().items()]  # type: ignore

    @classmethod
    def get_key_list(cls) -> list:
        return [key for key, value in cls.obj().items()]  # type: ignore

    @classmethod
    def get_value(cls, key: int):
        return cls.obj().get(int(key))  # type: ignore

    @classmethod
    def get_key(cls, value):
        for k, v in cls.obj().items():  # type: ignore
            if v == value:
                return k

    @classmethod
    def get_select(cls):
        return [ComboBoxDataModel(id=str(_id), name=name) for _id, name in cls.obj().items()]  # type: ignore
