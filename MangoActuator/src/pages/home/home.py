# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-27 14:45
# @Author : 毛鹏

from mango_ui import *
from mango_ui.init import *
from src.models.user_model import UserModel

class HomePage(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.label_6 = MangoLabel(f'欢迎{UserModel().nickname}使用芒果测试平台！', self)
        self.layout.addWidget(self.label_6)

    def show_data(self):
        pass

    def signal_label_6(self, text):
        self.label_6.setText(text)
