# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-07-07 10:14
# @Author : 毛鹏
from exceptions import MangoActuatorError


class UiError(MangoActuatorError):
    pass


class BrowserPathError(UiError):
    pass


class ElementOpeNoneError(UiError):
    pass


class BrowserObjectClosed(UiError):
    pass


class UiTimeoutError(UiError):
    pass


class ElementTypeError(UiError):
    pass


class UiAssertionError(UiError):
    pass


class UiSqlAssertionError(UiError):
    pass


class LocatorError(UiError):
    pass


class ElementIsEmptyError(UiError):
    pass


class ElementLocatorError(UiError):
    pass


class UiAttributeError(UiError):
    pass


class UploadElementInputError(UiError):
    pass


class UiCacheDataIsNullError(UiError):
    pass


class ReplaceElementLocatorError(UiError):
    pass


class ScreenshotError(UiError):
    pass


class ElementNotFoundError(UiError):
    pass


class ElementNotDisappearError(UiError):
    pass


class NewObjectError(UiError):
    pass

class NoBrowserError(UiError):
    pass


class PackageNameError(UiError):
    pass


class UrlError(UiError):
    pass


class XpathElementNoError(UiError):
    pass
