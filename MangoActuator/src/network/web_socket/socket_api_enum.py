# -*- coding: utf-8 -*-
# @Project: 执行器调用服务器
# @Description: 
# @Time   : 2023-12-12 12:42
# @Author : 毛鹏
import asyncio
from enum import Enum


class ApiSocketEnum(Enum):
    """ api自动化接口 """
    RECORDING_API = "a_recording_api"  # 录制接口


class UiSocketEnum(Enum):
    """ UI自动化接口 """
    PAGE_STEPS = 'u_page_steps'  # 步骤详情
    TEST_CASE = 'u_test_case'  #
    TEST_CASE_BATCH = 'u_test_suite_details'  #


class PytestSocketEnum(Enum):
    """ Pytest自动化接口 """
    TEST_CASE_BATCH = 'p_test_suite_details'  #
    TEST_CASE = 'p_test_case'  #


class ToolsSocketEnum(Enum):
    """ 工具类接口 """
    SET_OPERATION_OPTIONS = 't_set_operation_options'
    SET_USERINFO = 't_set_userinfo'
    GET_TASK = 't_get_task'  #


class QueueEnum(Enum):
    """ 队列 """
    WEB_SOCKET = asyncio.Queue()
