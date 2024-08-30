# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-08-30 14:51
# @Author : 毛鹏
from PySide6.QtWidgets import QDialog


class MangoDialog(QDialog):
    def __init__(self, tips: str, size: super = (400, 300)):
        super().__init__()
        self.setWindowTitle(tips)
        self.setFixedSize(*size)  # 设置窗口大小
