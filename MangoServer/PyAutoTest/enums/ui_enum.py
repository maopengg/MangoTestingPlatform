# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2022-12-06 21:05
# @Author : 毛鹏
from enum import Enum


class BrowserTypeEnum(Enum):
    CHROMIUM = 0
    FIREFOX = 1
    WEBKIT = 2


class UiPublicTypeEnum(Enum):
    """ {"0": "CUSTOM"}，{"1": "SQL"}，{"2": "HEAD"} """
    CUSTOM = 0
    SQL = 1


class ElementExpEnum(Enum):
    """ {0: "W_XPATH"}，{1: "W_ID"}，{3: "W_文本"}，{4: "W_占位符"}，{5: "W_CSS"}，{11: "A_DESCRIPTION"}，{12: "A_BOUNDS"}，{13: "A_百分比坐标点击"} """
    XPATH = 0
    ID = 1
    TEXT = 3
    PLACEHOLDER = 4
    CSS = 5
    # APP专属
    DESCRIPTION = 11
    BOUNDS = 12
    PERCENTAGE = 13


class StateEnum(Enum):
    """ 0 是未测试，1 是失败，2 是通过"""
    NOT = 0
    FAIL = 1
    ADOPT = 2
