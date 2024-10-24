# -*- coding: utf-8 -*-
# @Project: 芒果测试平台# @Description:
# @Time   : 2023-07-16 15:17
# @Author : 毛鹏
from src.exceptions.mango_error import MangoActuatorError


class ToolsError(MangoActuatorError):
    pass


class MysqlConnectionError(ToolsError):
    pass


class MysqlQueryError(ToolsError):
    pass


class MysqlQueryIsNullError(ToolsError):
    pass


class CacheIsEmptyError(ToolsError):
    pass


class SyntaxErrorError(ToolsError):
    pass


class FileDoesNotEexistError(ToolsError):
    pass


class JsonPathError(ToolsError):
    pass


class ValueTypeError(ToolsError):
    pass


class FileNotError(ToolsError):
    pass


class SendMessageError(ToolsError):
    pass
