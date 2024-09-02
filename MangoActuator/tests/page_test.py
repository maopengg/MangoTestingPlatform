# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-09-02 10:38
# @Author : 毛鹏

from PySide6.QtWidgets import QApplication

from src.login_window import LoginLogic

if __name__ == '__main__':
    app = QApplication([])
    window = LoginLogic()
    app.exec()
