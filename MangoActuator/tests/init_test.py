# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-10-08 16:12
# @Author : 毛鹏
from PySide6.QtWidgets import QWidget, QVBoxLayout, QApplication, QPushButton, QFormLayout
from mango_ui import *


class MyQWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)  # 设置间距为0
        self.resize(800, 400)
        self.layout_1 = QFormLayout()
        self.layout_1.addWidget(MangoPushButton('按钮'))
        self.layout_1.addWidget(MangoLabel('哈哈哈'))
        self.widget = MangoCard(self.layout_1)
        self.layout.addWidget(self.widget)
        self.layout.addWidget(QPushButton('2'))
        self.setLayout(self.layout)


if __name__ == '__main__':
    app = QApplication([])
    window = MyQWidget()
    window.show()
    app.exec()
