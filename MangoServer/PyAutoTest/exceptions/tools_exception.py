# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-07-16 15:17
# @Author : 毛鹏

class MysqlAbnormalConnection(Exception):
    def __init__(self, msg):
        self.code = 301
        self.msg = msg
