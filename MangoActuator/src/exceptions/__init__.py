# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2023-07-07 10:14
# @Author : 毛鹏
from src.exceptions.error_msg import *
from src.tools.log_collector import log


class MangoActuatorError(Exception):

    def __init__(self, code: int, msg: str, value: tuple = None, error: any = None):
        self.code = code
        if value:
            self.msg = msg.format(*value)
        else:
            self.msg = msg
        log.error(f'报错提示：{self.msg}， 报错内容：{error}')


class UiError(MangoActuatorError):
    pass


class ToolsError(MangoActuatorError):
    pass


class ApiError(MangoActuatorError):
    pass
