# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-10-24 18:11
# @Author : 毛鹏
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from mango_ui import *

from .small_tools_dict import tools_data


class SmallToolsPage(QWidget):

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(20, 20, 20, 20)

        self.setLayout(self.layout)

    def show_data(self):
        for index, i in enumerate(tools_data):
            if index % 3 == 0 or index == 0:
                layout_h = QHBoxLayout()
                self.layout.addLayout(layout_h)
            layout_v = QVBoxLayout()
            mango_card = MangoCard(layout_v, name=i["title"])
            mango_card.clicked.connect(self.card_click)
            layout_h.addWidget(mango_card)
            layout_v.addWidget(MangoLabel(f'名称：{i["title"]}'))
            layout_v.addWidget(MangoLabel(f'描述：{i["describe"]}'))

        self.layout.addStretch()

    def card_click(self, data):
        for i in tools_data:
            if i.get('title') == data:
                url = QUrl(i.get('url'))  # 替换为你想要打开的 URL
                QDesktopServices.openUrl(url)
