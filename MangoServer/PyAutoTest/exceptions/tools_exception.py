# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-07-16 15:17
# @Author : 毛鹏
from PyAutoTest.exceptions import MangoServerError


class MysqlAbnormalConnection(MangoServerError):
    def __init__(self, msg):
        self.code = 301
        self.msg = msg


class JsonPathError(MangoServerError):
    def __init__(self, msg):
        self.code = 300
        self.msg = msg


class JsonSerializeError(MangoServerError):
    def __init__(self, msg):
        self.code = 300
        self.msg = msg


class ValueTypeError(MangoServerError):
    def __init__(self, msg):
        self.code = 300
        self.msg = msg


class SendMessageError(MangoServerError):

    def __init__(self, msg):
        self.code = 300
        self.msg = msg


class DoesNotExistError(MangoServerError):

    def __init__(self, msg):
        self.code = 300
        self.msg = msg


class MysqlConfigError(MangoServerError):

    def __init__(self, msg):
        self.code = 300
        self.msg = msg


class MySQLConnectionFailureError(MangoServerError):

    def __init__(self, msg):
        self.code = 300
        self.msg = msg


class SQLGrammarError(MangoServerError):

    def __init__(self, msg):
        self.code = 300
        self.msg = msg


class FileDoesNotEexistError(MangoServerError):

    def __init__(self, msg):
        self.code = 300
        self.msg = msg


class CacheIsEmptyError(MangoServerError):

    def __init__(self, msg):
        self.code = 300
        self.msg = msg


class SocketClientNotPresentError(MangoServerError):

    def __init__(self, msg):
        self.code = 300
        self.msg = msg
