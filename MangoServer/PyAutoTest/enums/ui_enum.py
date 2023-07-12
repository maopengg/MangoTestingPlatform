# -*- coding: utf-8 -*-
# @Project: auto_test
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
    """ {0: "XPATH"}，{1: "ID"}，{2: "NAME"}，{3: "TEXT"}，{4: "占位符"}，{5: "CSS"}，{11: "DESCRIPTION"}，{12: "BOUNDS"}，{13: "百分比坐标点击"} """
    XPATH = 0
    ID = 1
    NAME = 2
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
