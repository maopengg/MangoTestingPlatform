# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-08-30 14:08
# @Author : 毛鹏
from src import *
from src.models.gui_model import SearchDataModel

from src.widgets import *


class SearchWidget(QWidget):
    clicked = Signal(object)

    def __init__(self, search_data: list[SearchDataModel]):
        super().__init__()
        self.search_data = search_data
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        self.v_layout = QVBoxLayout()
        self.v_layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addLayout(self.v_layout)
        for index, search in enumerate(self.search_data):
            if index % 4 == 0 or index == 0:
                but_layout = QHBoxLayout()
                but_layout.setContentsMargins(0, 0, 0, 0)
                self.v_layout.addLayout(but_layout)
            from_layout = QFormLayout()
            intput = MangoLineEdit(search.placeholder, '', )
            from_layout.addRow(f'{search.title}：', intput)
            but_layout.addLayout(from_layout)
            search.input = intput
            if (index + 1) % 4 == 0 or index == len(self.search_data) - 1:
                if (index + 1) % 4 != 0:
                    but_layout.addStretch()

        self.layout.addStretch()
        self.search_but = MangoPushButton('搜索', bg_color=THEME.blue)
        self.search_but.setMinimumHeight(30)  # 设置最小高度
        self.search_but.setMinimumWidth(50)
        self.search_but.clicked.connect(self.on_search_but_clicked)

        self.layout.addWidget(self.search_but)

        self.reset_but = MangoPushButton('重置', bg_color=THEME.red)
        self.reset_but.setMinimumHeight(30)  # 设置最小高度
        self.reset_but.setMinimumWidth(50)
        self.reset_but.clicked.connect(self.on_reset_but_clicked)
        self.layout.addWidget(self.reset_but)

        self.layout.addLayout(self.layout)

    def on_reset_but_clicked(self):
        for search in self.search_data:
            search.input.setText('')
        self.clicked.emit({})

    def on_search_but_clicked(self):
        data = {}
        for search in self.search_data:
            value = search.input.text()
            if value:
                data[search.key] = value
        self.clicked.emit(data)
