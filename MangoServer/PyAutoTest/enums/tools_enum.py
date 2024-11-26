# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-12-08 9:50
# @Author : 毛鹏

from PyAutoTest.enums import BaseEnum


class ClientTypeEnum(BaseEnum):
    """
    三个端的类型
    """
    SERVER = 0
    WEB = 1
    ACTUATOR = 2

    @classmethod
    def obj(cls):
        return {0: "服务端", 1: "控制端", 2: "执行端"}


class ClientNameEnum(BaseEnum):
    """
    端名称
    """
    DRIVER = 'Mango Actuator'
    SERVER = 'Mango Server'
    WEB = 'mango-console'
    PLATFORM_CHINESE = '芒果测试平台'
    PLATFORM_ENGLISH = 'MangoTestPlatform'

    @classmethod
    def obj(cls):
        return {'DRIVER': "Mango Actuator", 'SERVER': "Mango Server", 'WEB': "mango-console"}


class StatusEnum(BaseEnum):
    """状态枚举"""
    SUCCESS = 1
    FAIL = 0

    @classmethod
    def obj(cls):
        return {0: "关闭&进行中&失败", 1: "启用&已完成&通过"}


class TaskEnum(BaseEnum):
    """状态枚举"""
    FAIL = 0
    SUCCESS = 1
    STAY_BEGIN = 2
    PROCEED = 3

    @classmethod
    def obj(cls):
        return {0: "失败", 1: "通过", 2: "待开始", 3: "进行中"}


class ProductTypeEnum(BaseEnum):
    """产品类型"""
    WEB = 0
    PC = 1
    APP = 2
    ANDROID = 3
    IOS = 4
    MINI = 5

    @classmethod
    def obj(cls):
        return {
            0: "WEB（API,UI通用）",
            1: "PC桌面（API,UI通用）",
            2: "APP（API专用）",
            3: '安卓（UI专用）',
            4: 'IOS（UI专用）',
            5: '小程序（API专用）'
        }


class AutoTypeEnum(BaseEnum):
    """产品类型"""
    CURRENCY = 0
    UI = 1
    API = 2

    @classmethod
    def obj(cls):
        return {0: "前端&接口通用", 1: "前端自动化", 2: "接口自动化"}
