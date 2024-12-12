# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2023-07-07 10:14
# @Author : 毛鹏

from PyAutoTest.exceptions.error_msg import *
from PyAutoTest.tools.log_collector import log


class MangoServerError(Exception):

    def __init__(self, code: int, msg: str, value: tuple = None, error: str = None, is_log=True):
        self.code = code
        if value:
            self.msg = msg.format(*value)
        else:
            self.msg = msg
        if error and is_log:
            log.system.error(f'报错提示：{msg}， 报错内容：{error}')
        else:
            log.system.error(f'报错提示：{msg}')


class UiError(MangoServerError):
    pass


class ApiError(MangoServerError):
    pass


class ToolsError(MangoServerError):
    pass


class PerfError(MangoServerError):
    pass


class SystemEError(MangoServerError):
    pass


class UserError(MangoServerError):
    pass


if __name__ == '__main__':
    ddd = MangoServerError(*ERROR_MSG_0011, value=(1,))
    print(ddd.msg)
    print(ddd.code)
