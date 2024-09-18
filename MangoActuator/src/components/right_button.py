# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description:
# @Time   : 2024-08-30 14:08
# @Author : 毛鹏
from functools import partial

from src import *
from src.models.gui_model import RightDataModel
from src.widgets import *


class RightButton(QWidget):
    clicked = Signal(object)

    def __init__(self, but_list_obj: list[RightDataModel]):
        super().__init__()
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addStretch()
        for but_obj in but_list_obj:
            but = MangoPushButton(but_obj.name, bg_color=but_obj.theme)
            but.clicked.connect(partial(self.but_clicked, but_obj.action))
            self.layout.addWidget(but)
        self.setLayout(self.layout)

    def but_clicked(self, action):
        self.clicked.emit({'action': action, 'row': None})
