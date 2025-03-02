# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-04 17:21
# @Author : 毛鹏
from src.enums import BaseEnum


class TipsTypeEnum(BaseEnum):
    ERROR = 0
    SUCCESS = 1
    INFO = 2
    WARNING = 3
    RESPONSE = 4
