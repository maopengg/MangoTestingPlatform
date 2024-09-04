# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-09-04 17:43
# @Author : 毛鹏

from PySide6.QtWidgets import QApplication

from src.components import *

if __name__ == '__main__':
    app = QApplication([])
    window = DialogWidget()
    window.show()
    app.exec()
