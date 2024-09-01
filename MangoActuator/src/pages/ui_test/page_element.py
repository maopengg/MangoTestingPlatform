# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2024-09-01 下午9:01
# @Author : 毛鹏
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel


class PageElementPage(QWidget):
    def __init__(self, text):
        super().__init__()
        self.layout = QVBoxLayout()
        self.label = QLabel("加载中...")
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)
        self.text = text

    def load_data(self):
        # 模拟延迟加载数据
        QTimer.singleShot(3000, self.show_data)  # 3秒后调用show_data方法

    def show_data(self):
        self.label.setText(self.text)
