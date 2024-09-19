# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-04 14:36
# @Author : 毛鹏
from PySide6.QtCore import QPoint

from src.settings.settings import THEME
from src.widgets import *


def success_notification(parent, text):
    notification = MangoNotification(parent, text, THEME.green)
    # 获取主窗口右上角位置
    parent_pos = parent.mapToGlobal(QPoint(parent.width() - notification.width() - 10, 20))
    notification.move(parent_pos)
    notification.show()


def info_notification(parent, text):
    notification = MangoNotification(parent, text, THEME.pink)
    # 获取主窗口右上角位置
    parent_pos = parent.mapToGlobal(QPoint(parent.width() - notification.width() - 10, 20))
    notification.move(parent_pos)
    notification.show()


def warning_notification(parent, text):
    notification = MangoNotification(parent, text, THEME.yellow)
    # 获取主窗口右上角位置
    parent_pos = parent.mapToGlobal(QPoint(parent.width() - notification.width() - 10, 20))
    notification.move(parent_pos)
    notification.show()


def error_notification(parent, text):
    notification = MangoNotification(parent, text, THEME.red)
    # 获取主窗口右上角位置
    parent_pos = parent.mapToGlobal(QPoint(parent.width() - notification.width() - 10, 20))
    notification.move(parent_pos)
    notification.show()
