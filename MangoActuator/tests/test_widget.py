# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-09-04 17:43
# @Author : 毛鹏
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget, QVBoxLayout, QApplication

from src.widgets import *


class MyQWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        combo_box = MangoComboBox('选择框')
        # 添加选项
        combo_box.addItems(['选项1', '选项2', '选项3', '选项4'])
        # 设置默认选项
        combo_box.setCurrentIndex(0)  # 默认选择第一个选项
        # combo_box.setWindowIcon(QIcon(':/resources/icons/down.svg'))
        self.layout.addWidget(combo_box)
        self.setLayout(self.layout)


if __name__ == '__main__':
    app = QApplication([])
    window = MyQWidget()
    window.show()
    app.exec()
