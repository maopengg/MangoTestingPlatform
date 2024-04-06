# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-07-07 10:14
# @Author : 毛鹏
import logging

from PyAutoTest.tools.view_utils.error_msg import ERROR_MSG_0011

log = logging.getLogger('system')


class MangoServerError(Exception):

    def __init__(self, code: int, msg: str, value: tuple = None, error: str = None, is_log=True):
        if value:
            msg = msg.format(*value)
        if error and is_log:
            log.error(f'报错提示：{msg}， 报错内容：{error}')
        else:
            log.error(f'报错提示：{msg}')
        self.code = code
        self.msg = msg


if __name__ == '__main__':
    ddd = MangoServerError(*ERROR_MSG_0011, value=(1,))
    print(ddd.msg)
    print(ddd.code)
