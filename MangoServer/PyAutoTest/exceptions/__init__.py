# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-07-07 10:14
# @Author : 毛鹏
from PyAutoTest.tools.view_utils.error_msg import ERROR_MSG_0011


class MangoServerError(Exception):

    def __init__(self, code: int, msg: str, value: tuple = None):
        if value:
            msg = msg.format(*value)
        self.code = code
        self.msg = msg


if __name__ == '__main__':
    ddd = MangoServerError(*ERROR_MSG_0011, value=(1, ))
    print(ddd.msg)
    print(ddd.code)
