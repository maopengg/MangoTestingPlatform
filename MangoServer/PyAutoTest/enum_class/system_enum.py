# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-05-06 8:34
# @Author : 毛鹏
from enum import Enum


class NoticeEnum(Enum):
    """ 1是邮件，2是企微 """
    MAIL = 0
    WECOM = 1
