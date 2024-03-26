# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-07-07 10:14
# @Author : 毛鹏
from tools.logging_tool import logger


class MangoActuatorError(Exception):

    def __init__(self, code: int, msg: str, value: tuple = None, error: any = None, is_log: bool = True):
        if error and is_log:
            logger.error(f'错误code码：{code}, 消息：{msg}, 系统异常消息：{error}')
        self.code = code
        self.msg = msg.format(*value) if value else msg
