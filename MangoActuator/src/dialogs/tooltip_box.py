# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-05-27 13:04
# @Author : 毛鹏
from PySide6.QtWidgets import QMessageBox


def show_failed_message(text: str, title: str = '失败'):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setText(text)
    msg.setWindowTitle(title)
    msg.exec()


def show_success_message(text: str, title: str = '成功'):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Information)
    msg.setText(text)
    msg.setWindowTitle(title)
    msg.exec()


def show_warning_message(text: str, title: str = '警告'):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Warning)
    msg.setText(text)
    msg.setWindowTitle(title)
    msg.exec()


def show_info_message(text: str, title: str = '提示'):
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Information)
    msg.setText(text)
    msg.setWindowTitle(title)
    msg.exec()
