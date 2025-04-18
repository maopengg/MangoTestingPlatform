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
    GET_TASK = 'u_get_task'  #


class ToolsSocketEnum(Enum):
    """ 工具类接口 """
    SET_OPERATION_OPTIONS = 't_set_operation_options'
    SET_USER_OPEN_STATUS_OPTIONS = 't_set_actuator_open_state'


class QueueEnum(Enum):
    """ 队列 """
    WEB_SOCKET = asyncio.Queue()
