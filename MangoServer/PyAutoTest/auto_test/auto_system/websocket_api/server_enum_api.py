# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-09 11:49
# @Author : 毛鹏
from enum import Enum


class ServerEnumAPI(Enum):
    # 调用CMD
    CMD = 'cmd'
    NUW_WEB_OBJ = 'new_web_obj'
    NUW_APP_OBJ = 'new_app_obj'
    UI_CASE_RUN = 'ui_case_run'
