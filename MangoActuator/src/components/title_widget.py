# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description:
# @Time   : 2024-08-30 14:08
# @Author : 毛鹏
from src import *
from src.models.gui_model import TitleDataModel

from src.widgets import *


class TitleWidget(QWidget):
    clicked = Signal(object)

    def __init__(self, title_data: list[TitleDataModel]):
        super().__init__()
        self.setContentsMargins(0, 0, 0, 0)
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

        self.title_data = title_data
        for search in self.title_data:
            from_layout = QFormLayout()
            intput = MangoLineEdit('', search.placeholder)
            from_layout.addRow(f'{search.title}：', intput)
            self.layout.addLayout(from_layout)
            search.input = intput

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
        for search in self.title_data:
            search.input.setText('')
        self.clicked.emit({})

    def on_search_but_clicked(self):
        data = {}
        for search in self.title_data:
            value = search.input.text()
            if value:
                data[search['key']] = value
        self.clicked.emit(data)


if __name__ == '__main__':
    app = QApplication()
    window = TitleWidget()
    window.show()
    app.exec()
