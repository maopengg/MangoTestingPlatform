# -*- coding: utf-8 -*-
# @Project: 服务器调用执行器
# @Description:
# @Time   : 2023-06-04 12:24
# @Author : 毛鹏
from enum import Enum


class ApiSocketEnum(Enum):
    API_INFO = 'a_api_info'
    API_CASE = 'a_api_case'


class UiSocketEnum(Enum):
    PAGE_STEPS = 'u_page_step'
    CASE_BATCH = 'u_case'
    NEW_PAGE_OBJ = 'u_page_new_obj'
    MangoPytest = 't_mango_pytest'
    RECORDING = 'u_recording'
    SET_OPEN_STATUS = 't_set_open_status'


class ToolsSocketEnum(Enum):
    pass


class PytestSocketEnum(Enum):
    TEST_CASE = 'p_case'
