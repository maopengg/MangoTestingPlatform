# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-05-06 8:34
# @Author : 毛鹏
from enum import Enum


class NoticeEnum(Enum):
    """ {"0": "邮箱"}，{"1": "企微"}，{"2": "钉钉-未测试"} """
    MAIL = 0
    WECOM = 1
    NAILING = 2


class EnvironmentEnum(Enum):
    """ {"0": "测试环境"}，{"1": "预发环境"}，{"2": "生产环境"} """
    TEST = 0
    PRE = 1
    PRO = 2


class AutoTestTypeEnum(Enum):
    """ {"0": "界面自动化"}，{"1": "接口自动化"}，{"2": "性能自动化"} """
    UI = 0
    API = 1
    PERF = 2

    @classmethod
    def get(cls, value):
        return {
            0: "界面自动化",
            1: "接口自动化",
            2: "性能自动化"
        }[value]

class DevicePlatformEnum(Enum):
    """ {"0": "web"}，{"1": "安卓"}，{"2": "IOS"}，{"3": "桌面PC"} """
    WEB = 0
    ANDROID = 1
    IOS = 2
    DESKTOP = 3


class SocketEnum(Enum):
    web_path = '/web/socket'
    client_path = '/client/socket'
    common_actuator_name = 'admin'
    client_conn_obj = 'client_obj'
    web_conn_obj = 'web_obj'


class ClientTypeEnum(str, Enum):
    ACTUATOR = "actuator"
    WEB = "web"
    SERVER = "server"


class IsItEnabled(Enum):
    right = 1
    wrong = 0
