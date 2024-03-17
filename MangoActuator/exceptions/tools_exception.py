# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-07-16 15:17
# @Author : 毛鹏
from exceptions import MangoActuatorError


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
