# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description:
# @Time   : 2024-08-30 14:08
# @Author : 毛鹏
from PySide6.QtWidgets import *

from src.widgets import *


class RightButton(QWidget):
    def __init__(self, but_list_obj: list[dict]):
        super().__init__()
        self.setContentsMargins(0, 0, 0, 0)
        self.layout = QHBoxLayout()
        self.layout.addStretch()
        self.but_list: list[dict] = []
        for but_obj in but_list_obj:
            but = PyPushButton(but_obj['name'], bg_color=but_obj['theme'])
            but.clicked.connect(but_obj['func'])
            but.setMinimumWidth(50)
            but.setMinimumHeight(30)
            self.layout.addWidget(but)
            self.but_list.append({but_obj['name']: but})
        self.setLayout(self.layout)


if __name__ == '__main__':
    app = QApplication()
    window = RightButton()
    window.show()
    app.exec()
