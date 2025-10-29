# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2022-12-06 21:05
# @Author : 毛鹏
from src.enums import BaseEnum


class DriveTypeEnum(BaseEnum):
    """UI自动化平台枚举"""
    WEB = 0
    ANDROID = 1
    DESKTOP = 2

    @classmethod
    def obj(cls):
        return {0: "WEB", 1: "安卓", 2: "PC桌面"}


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
    # TEST_ID = 1
    LOCATOR = 2
    TEXT = 3
    PLACEHOLDER = 4
    # LABEL = 5
    # TITLE = 6
    # ROLE = 7
    # AIT_TEXT = 8
    CSS = 9
    # APP专属
    DESCRIPTION = 11
    BOUNDS = 12
    # PERCENTAGE = 13
    RESOURCE_ID = 14

    @classmethod
    def obj(cls):
        return {
            0: "XPATH",
            # 1: "W_TestID",
            2: "通用定位器",
            3: "WEB_文本",
            4: "WEB_占位符",
            # 5: "W_标签",
            # 6: "W_标题",
            # 7: "W_ROLE",
            # 8: "W_AIT_TEXT",
            9: "WEB_CSS",
            11: "安卓_description",
            12: "安卓_bounds",
            # 13: "A_百分比坐标点击",
            14: "安卓_resourceId",
        }


class ElementOperationEnum(BaseEnum):
    """元素操作类型枚举"""
    OPE = 0
    ASS = 1
    SQL = 2
    CUSTOM = 3
    CONDITION = 4
    PYTHON_CODE = 5

    @classmethod
    def obj(cls):
        return {0: "元素操作", 1: "断言操作", 2: "SQL变量", 3: "自定义变量", 4: "条件判断", 5: "python代码"}


class UiPublicTypeEnum(BaseEnum):
    """全局变量类型"""
    CUSTOM = 0
    SQL = 1

    @classmethod
    def obj(cls):
        return {0: "自定义-第一加载", 1: "SQL-第二加载"}
