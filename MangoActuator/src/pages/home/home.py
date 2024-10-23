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
        self.mango_dialog = MangoDialog('添加作者微信进芒果测试平台交流群', (260, 340))
        label = QLabel()
        pixmap = QPixmap(":/picture/author.png")  # 替换为你的图片路径
        label.setPixmap(pixmap)
        label.setScaledContents(True)  # 允许缩放
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 设置大小策略
        self.mango_dialog.layout.addWidget(label)


    def show_data(self):
        QTimer.singleShot(1000, self.open_dialog)  # 1000毫秒后调用open_dialog方法

    def open_dialog(self):
        self.mango_dialog.exec()

    def signal_label_6(self, text):
        self.label_6.setText(text)
