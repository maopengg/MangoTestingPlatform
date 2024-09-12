# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-09-04 17:43
# @Author : 毛鹏
from PySide6.QtWidgets import QWidget, QVBoxLayout, QApplication

from src.enums.tools_enum import StatusEnum
from src.models.gui_model import ComboBoxDataModel
from src.widgets import *


class MyQWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.setFixedSize(500, 350)
        data: list[ComboBoxDataModel] = StatusEnum.get_select()
        combo_box = MangoComboBox('请选择状态', data)
        # 添加选项

        # combo_box.setWindowIcon(QIcon(':/icons/icons/down.svg'))
        self.layout.addWidget(combo_box)
        self.setLayout(self.layout)


if __name__ == '__main__':
    app = QApplication([])
    window = MyQWidget()
    window.show()
    app.exec()
