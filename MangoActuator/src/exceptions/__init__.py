# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-07-07 10:14
# @Author : 毛鹏
from src.exceptions.error_msg import (
    ERROR_MSG_0001,
    ERROR_MSG_0003,
    ERROR_MSG_0004,
    ERROR_MSG_0005,
    ERROR_MSG_0007,
    ERROR_MSG_0010,
    ERROR_MSG_0025,
    ERROR_MSG_0026,
)
from src.settings import settings
from src.tools.log_collector import log


class MangoActuatorError(Exception):

    def __init__(self, code: int, msg: str, value: tuple = None, error: any = None):
        self.msg = msg.format(*value) if value else msg
        self.code = code
        if settings.IS_DEBUG:
            if error:
                log.error(f'{self.msg}，报错内容：{error}')
            else:
                log.error(self.msg)

    def __str__(self):
        return f"[{self.code}] {self.msg}"


class UiError(MangoActuatorError):
    pass


class ToolsError(MangoActuatorError):
    pass


class ApiError(MangoActuatorError):
    pass
