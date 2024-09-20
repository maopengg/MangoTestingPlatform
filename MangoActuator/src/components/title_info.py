# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-08-30 14:08
# @Author : 毛鹏
# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-08-30 14:08
# @Author : 毛鹏
from src import *
from src.widgets import *
from src.models.gui_model import FieldListModel


class TitleInfoWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.field_list = None
        self.raw_data = None
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.form_layout = QFormLayout()
        self.mango_card = MangoCardWidget(self.form_layout)
        self.layout.addWidget(self.mango_card)
        self.setLayout(self.layout)

    def init(self, raw_data: dict, field_list: list[FieldListModel]):
        if self.field_list is None and self.raw_data is None:
            self.field_list = field_list
            self.raw_data = raw_data
            for i in self.field_list:
                self.form_layout.addRow(f"{i.name}：", MangoLabel(f'{self.raw_data[i.key]}'))
