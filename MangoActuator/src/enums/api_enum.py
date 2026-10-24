# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-06-04 12:24
# @Author : 毛鹏
from src.enums import BaseEnum


class ClientEnum(BaseEnum):
    """设备类型"""
    WEB = 0
    APP = 1
    PC = 2
    MINI = 3

    @classmethod
    def obj(cls):
        return {0: "WEB", 1: "PC桌面", 2: "APP", 3: "小程序", }
