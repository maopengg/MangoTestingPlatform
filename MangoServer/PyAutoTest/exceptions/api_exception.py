# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: # @Time   : 2023-07-15 13:22
# @Author : 毛鹏
from PyAutoTest.exceptions import MangoServerError


class CacheIsNone(MangoServerError):
    pass


class AgentError(MangoServerError):
    pass


class LoginError(MangoServerError):
    pass


class UnknownError(MangoServerError):
    pass


class AssError(MangoServerError):
    pass


class SqlAssError(AssError):
    pass


class ResponseWholeAssError(AssError):
    pass


class ResponseValueAssError(AssError):
    pass


class ResponseSyntaxError(MangoServerError):
    pass


class CaseIsEmptyError(MangoServerError):
    pass


class PublicMysqlError(MangoServerError):
    pass


class DumpDataError(MangoServerError):
    pass


class SqlResultIsNoneError(MangoServerError):
    pass
