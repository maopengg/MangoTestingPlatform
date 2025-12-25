# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-08-25 15:22
# @Author : 毛鹏


from mangoui.widgets.display import MangoLabel
from mangoui.widgets.layout import MangoHBoxLayout, MangoGridLayout
from mangoui.widgets.window import MangoWidget


class PcPage(MangoWidget):

    def __init__(self, parent, ):
        super().__init__(parent)
        self.parent = parent
        self.data = []
        self.layout.setContentsMargins(10, 10, 10, 10)

        h_layout = MangoHBoxLayout()
        card_layout = MangoGridLayout()
        h_layout.addLayout(card_layout)
        h_layout.addStretch()

        card_layout.addWidget(MangoLabel('还没有配置'))

        self.layout.addLayout(h_layout)
        self.layout.addStretch()

    def load_page_data(self):
        pass
