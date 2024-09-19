# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-04 14:35
# @Author : 毛鹏
from PySide6.QtCore import QPoint

from src.models.network_model import ResponseModel
from src.settings.settings import THEME
from src.widgets import *


def info_message(parent, text):
    message = MangoMessage(parent, text, THEME.pink)
    parent_pos = parent.mapToGlobal(QPoint(parent.width() // 2 - message.width() // 2, 0))
    message.move(parent_pos)
    message.show()


def success_message(parent, text):
    message = MangoMessage(parent, text, THEME.green)
    parent_pos = parent.mapToGlobal(QPoint(parent.width() // 2 - message.width() // 2, 0))
    message.move(parent_pos)
    message.show()


def warning_message(parent, text):
    message = MangoMessage(parent, text, THEME.yellow)
    parent_pos = parent.mapToGlobal(QPoint(parent.width() // 2 - message.width() // 2, 0))
    message.move(parent_pos)
    message.show()


def error_message(parent, text):
    message = MangoMessage(parent, text, THEME.red)
    parent_pos = parent.mapToGlobal(QPoint(parent.width() // 2 - message.width() // 2, 0))
    message.move(parent_pos)
    message.show()


def response_message(parent, response: ResponseModel):
    if response.code == 200:
        success_message(parent, response.msg)
    else:
        error_message(parent, response.msg)
