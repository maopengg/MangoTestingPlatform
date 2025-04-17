# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-27 14:45
# @Author : 毛鹏
from mangoui import *

from src.settings.settings import IS_WINDOW


class HomePage(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.page = 1
        self.page_size = 10
        self.parent = parent
        self.layout = MangoHBoxLayout(self)
        self.layout.addWidget(MangoLabel('首页-还在完善中~'))
        if IS_WINDOW:
            self.mango_dialog = MangoDialog('添加作者微信进芒果测试平台交流群', (260, 340))
            label = MangoLabel()
            pixmap = QPixmap(":/picture/author.png")  # 替换为你的图片路径
            label.setPixmap(pixmap)
            label.setScaledContents(True)  # 允许缩放
            label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # type: ignore
            self.mango_dialog.layout.addWidget(label)

    def show_data(self, ):
        pass

    def open_dialog(self):
        self.mango_dialog.exec()

    def pagination_clicked(self, data):
        if data['action'] == 'prev':
            self.page = data['page']
        elif data['action'] == 'next':
            self.page = data['page']
        elif data['action'] == 'per_page':
            self.page_size = data['page']
        self.show_data()
