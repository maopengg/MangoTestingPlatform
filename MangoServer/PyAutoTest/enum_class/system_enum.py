# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-05-06 8:34
# @Author : 毛鹏
from enum import Enum


class NoticeEnum(Enum):
    """ {"0": "邮件"}，{"1": "企微"}，{"2": "钉钉-未测试"} """
    MAIL = 0
    WECOM = 1
    NAILING = 2
