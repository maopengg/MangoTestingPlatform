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
    CASE_RESULT = 'u_case_result'  #


class ToolsSocketEnum(Enum):
    """ 工具类接口 """
    SET_OPERATION_OPTIONS = 't_set_operation_options'


class QueueEnum(Enum):
    """ 队列 """
    WEB_SOCKET = asyncio.Queue()
