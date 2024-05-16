# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-07-16 15:17
# @Author : 毛鹏
from PyAutoTest.exceptions import MangoServerError


class MysqlAbnormalConnection(MangoServerError):
    pass


class MysqlQueryIsNullError(MangoServerError):
    pass


class MysqlConnectionError(MangoServerError):
    pass


class SyntaxErrorError(MangoServerError):
    pass


class JsonPathError(MangoServerError):
    pass


class JsonSerializeError(MangoServerError):
    pass


class CacheKetNullError(MangoServerError):
    pass


class ValueTypeError(MangoServerError):
    pass


class SendMessageError(MangoServerError):
    pass


class DoesNotExistError(MangoServerError):
    pass


class MysqlConfigError(MangoServerError):
    pass


class MySQLConnectionFailureError(MangoServerError):
    pass


class MysqlQueryError(MangoServerError):
    pass


class FileDoesNotEexistError(MangoServerError):
    pass


class CacheIsEmptyError(MangoServerError):
    pass


class SocketClientNotPresentError(MangoServerError):
    pass


class InsideSaveError(MangoServerError):
    pass


class MiniIoConnError(MangoServerError):
    pass

class MiniIoFileError(MangoServerError):
    pass
