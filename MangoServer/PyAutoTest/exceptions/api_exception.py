# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-07-15 13:22
# @Author : 毛鹏
from PyAutoTest.exceptions import MangoServerError


class CacheIsNone(MangoServerError):
    def __init__(self, msg):
        self.code = 301
        self.msg = msg


class AgentError(MangoServerError):
    def __init__(self, msg):
        self.code = 301
        self.msg = msg


class LoginError(MangoServerError):
    def __init__(self, msg):
        self.code = 301
        self.msg = msg


class UnknownError(MangoServerError):
    def __init__(self, msg):
        self.code = 301
        self.msg = msg


class AssError(MangoServerError):
    def __init__(self, msg):
        self.code = 301
        self.msg = msg


class SqlAssError(AssError):
    def __init__(self, msg):
        self.code = 301
        self.msg = msg


class ResponseWholeAssError(AssError):
    def __init__(self, msg):
        self.code = 301
        self.msg = msg


class ResponseValueAssError(AssError):
    def __init__(self, msg):
        self.code = 301
        self.msg = msg


class ResponseSyntaxError(MangoServerError):
    def __init__(self, msg):
        self.code = 301
        self.msg = msg


class CaseIsEmptyError(MangoServerError):
    def __init__(self, msg):
        self.code = 301
        self.msg = msg


class PublicMysqlError(MangoServerError):
    def __init__(self, msg):
        self.code = 301
        self.msg = msg


class DumpDataError(MangoServerError):
    def __init__(self, msg):
        self.code = 301
        self.msg = msg
