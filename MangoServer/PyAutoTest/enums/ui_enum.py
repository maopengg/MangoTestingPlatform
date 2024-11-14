# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2022-12-06 21:05
# @Author : 毛鹏
from PyAutoTest.enums import BaseEnum


class DriveTypeEnum(BaseEnum):
    """UI自动化平台枚举"""
    WEB = 0
    ANDROID = 1
    DESKTOP = 2
    IOS = 3

    @classmethod
    def obj(cls):
        return {0: "WEB", 1: "安卓", 2: "PC桌面", 3: "IOS"}


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
    # PERCENTAGE = 13
    RESOURCE_ID = 14

    @classmethod
    def obj(cls):
        return {
            0: "XPATH",
            1: "W_TestID",
            2: "定位器",
            3: "W_文本",
            4: "W_占位符",
            5: "W_标签",
            6: "W_标题",
            7: "W_ROLE",
            8: "W_AIT_TEXT",
            9: "W_CSS",
            11: "A_DESCRIPTION",
            12: "A_BOUNDS",
            # 13: "A_百分比坐标点击",
            14: "A_resourceId",
        }




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


class DeviceEnum(BaseEnum):
    """浏览器设备枚举"""

    @classmethod
    def obj(cls):
        return ['Blackberry PlayBook', 'Blackberry PlayBook landscape', 'BlackBerry Z30', 'BlackBerry Z30 landscape',
                'Galaxy Note 3', 'Galaxy Note 3 landscape', 'Galaxy Note II', 'Galaxy Note II landscape',
                'Galaxy S III', 'Galaxy S III landscape', 'Galaxy S5', 'Galaxy S5 landscape', 'Galaxy S8',
                'Galaxy S8 landscape', 'Galaxy S9+', 'Galaxy S9+ landscape', 'Galaxy Tab S4', 'Galaxy Tab S4 landscape',
                'iPad (gen 6)', 'iPad (gen 6) landscape', 'iPad (gen 7)', 'iPad (gen 7) landscape', 'iPad Mini',
                'iPad Mini landscape', 'iPad Pro 11', 'iPad Pro 11 landscape', 'iPhone 6', 'iPhone 6 landscape',
                'iPhone 6 Plus', 'iPhone 6 Plus landscape', 'iPhone 7', 'iPhone 7 landscape', 'iPhone 7 Plus',
                'iPhone 7 Plus landscape', 'iPhone 8', 'iPhone 8 landscape', 'iPhone 8 Plus', 'iPhone 8 Plus landscape',
                'iPhone SE', 'iPhone SE landscape', 'iPhone X', 'iPhone X landscape', 'iPhone XR',
                'iPhone XR landscape', 'iPhone 11', 'iPhone 11 landscape', 'iPhone 11 Pro', 'iPhone 11 Pro landscape',
                'iPhone 11 Pro Max', 'iPhone 11 Pro Max landscape', 'iPhone 12', 'iPhone 12 landscape', 'iPhone 12 Pro',
                'iPhone 12 Pro landscape', 'iPhone 12 Pro Max', 'iPhone 12 Pro Max landscape', 'iPhone 12 Mini',
                'iPhone 12 Mini landscape', 'iPhone 13', 'iPhone 13 landscape', 'iPhone 13 Pro',
                'iPhone 13 Pro landscape', 'iPhone 13 Pro Max', 'iPhone 13 Pro Max landscape', 'iPhone 13 Mini',
                'iPhone 13 Mini landscape', 'Kindle Fire HDX', 'Kindle Fire HDX landscape', 'LG Optimus L70',
                'LG Optimus L70 landscape', 'Microsoft Lumia 550', 'Microsoft Lumia 550 landscape',
                'Microsoft Lumia 950', 'Microsoft Lumia 950 landscape', 'Nexus 10', 'Nexus 10 landscape', 'Nexus 4',
                'Nexus 4 landscape', 'Nexus 5', 'Nexus 5 landscape', 'Nexus 5X', 'Nexus 5X landscape', 'Nexus 6',
                'Nexus 6 landscape', 'Nexus 6P', 'Nexus 6P landscape', 'Nexus 7', 'Nexus 7 landscape',
                'Nokia Lumia 520', 'Nokia Lumia 520 landscape', 'Nokia N9', 'Nokia N9 landscape', 'Pixel 2',
                'Pixel 2 landscape', 'Pixel 2 XL', 'Pixel 2 XL landscape', 'Pixel 3', 'Pixel 3 landscape', 'Pixel 4',
                'Pixel 4 landscape', 'Pixel 4a (5G)', 'Pixel 4a (5G) landscape', 'Pixel 5', 'Pixel 5 landscape',
                'Moto G4', 'Moto G4 landscape', 'Desktop Chrome HiDPI', 'Desktop Edge HiDPI', 'Desktop Firefox HiDPI',
                'Desktop Safari', 'Desktop Chrome', 'Desktop Edge', 'Desktop Firefox']
