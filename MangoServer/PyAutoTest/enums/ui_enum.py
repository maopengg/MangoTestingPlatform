# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2022-12-06 21:05
# @Author : 毛鹏
from PyAutoTest.enums import BaseEnum


class BrowserTypeEnum(BaseEnum):
    """浏览器类型"""
    CHROMIUM = 0
    EDGE = 1
    FIREFOX = 2
    WEBKIT = 3

    @classmethod
    def obj(cls):
        return {0: "谷歌浏览器", 1: "EDGE", 2: "火狐", 3: "WEBKIT"}


class ElementExpEnum(BaseEnum):
    """元素定位方式枚举"""
    XPATH = 0
    TEST_ID = 1
    LOCATOR = 2
    TEXT = 3
    PLACEHOLDER = 4
    LABEL = 5
    TITLE = 6
    ROLE = 7
    AIT_TEXT = 8
    CSS = 9
    # APP专属
    DESCRIPTION = 11
    BOUNDS = 12
    PERCENTAGE = 13

    @classmethod
    def obj(cls):
        return {
            2: "定位器",
            0: "XPATH",
            1: "W_TestID",
            3: "W_文本",
            4: "W_占位符",
            5: "W_标签",
            6: "W_标题",
            7: "W_ROLE",
            8: "W_AIT_TEXT",
            9: "W_CSS",
            11: "A_DESCRIPTION",
            12: "A_BOUNDS",
            13: "A_百分比坐标点击"}


class DriveTypeEnum(BaseEnum):
    """UI自动化平台枚举"""
    WEB = 0
    ANDROID = 1
    DESKTOP = 2
    IOS = 3

    @classmethod
    def obj(cls):
        return {0: "WEB", 1: "安卓", 2: "PC桌面", 3: "IOS"}


class ElementOperationEnum(BaseEnum):
    """元素操作类型枚举"""
    OPE = 0
    ASS = 1
    SQL = 2
    CUSTOM = 3

    @classmethod
    def obj(cls):
        return {0: "操作", 1: "断言", 2: "SQL", 3: "参数"}


class UiPublicTypeEnum(BaseEnum):
    """公共参数类型"""
    CUSTOM = 0
    SQL = 1

    @classmethod
    def obj(cls):
        return {0: "自定义-第一加载", 1: "SQL-第二加载"}
