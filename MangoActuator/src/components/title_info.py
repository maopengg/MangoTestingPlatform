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
from PySide6.QtCore import Qt
from PySide6.QtWidgets import *

from src.models.gui_model import FieldListModel
from src.settings.settings import THEME


class TitleInfoWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.field_list = None
        self.raw_data = None

        # 创建 QFrame
        self.frame = QFrame(self)
        self.frame.setStyleSheet(f"""
            background-color: {THEME.dark_three};  /* 卡片背景色 */
            border: 1px solid lightgray; /* 边框 */
            border-radius: 10px;        /* 圆角 */
            padding: 10px;              /* 内部填充 */
        """)

        self.layout = QGridLayout(self.frame)
        self.layout.setSpacing(1)

        self.layout.setContentsMargins(0, 0, 0, 20)  # 内部间距
        self.layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.frame.setLayout(self.layout)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.frame)
        self.setLayout(main_layout)

    def init(self, raw_data: dict, field_list: list[FieldListModel]):
        self.field_list = field_list
        self.raw_data = raw_data
        row = 1  # 从1开始，因为第0行已经放了按钮
        for i in self.field_list:
            key_label = QLabel(f"{i.name}：")
            key_label.setAttribute(Qt.WA_NoSystemBackground)
            key_label.setContentsMargins(0, 0, 0, 0)
            value_label = QLabel(str(self.raw_data[i.key]))
            value_label.setAttribute(Qt.WA_NoSystemBackground)
            value_label.setContentsMargins(0, 0, 0, 0)
            self.layout.addWidget(key_label, row, 0, )
            self.layout.addWidget(value_label, row, 1, )
            row += 1
