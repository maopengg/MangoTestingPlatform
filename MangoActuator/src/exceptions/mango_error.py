# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-23 11:03
# @Author : 毛鹏
from src.tools.log_collector import log


class MangoActuatorError(Exception):

    def __init__(self, code: int, msg: str, value: tuple = None, error: any = None, is_log: bool = False):
        if value:
            msg = msg.format(*value)
        if error and is_log:
            log.error(f'报错提示：{msg}， 报错内容：{error}')
        elif is_log:
            log.warning(f'报错提示：{msg}')
        self.code = code
        self.msg = msg
