# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2022-12-06 21:05
# @Author : 毛鹏
from enum import Enum


class Environment(Enum):
    """ {"0": "测试环境"}，{"1": "预发环境"}，{"2": "生产环境"} """
    TEST = 0
    PRE = 1
    PROD = 2


class Notice(Enum):
    """ 1是邮件，2是企微 """
    MAIL = 0
    WECOM = 1
