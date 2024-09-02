# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description:
# @Time   : 2024-08-30 14:08
# @Author : 毛鹏
from PySide6.QtWidgets import *

from src.settings.settings import THEME
from src.widgets import *


class TitleWidget(QWidget):
    def __init__(self, ):
        super().__init__()
        self.setContentsMargins(0, 0, 0, 0)
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(self.layout)

        self.from_layout_1 = QFormLayout()
        self.intput_1 = PyLineEdit('', '请输入页面ID')
        self.from_layout_1.addRow('ID：', self.intput_1)

        self.from_layout_2 = QFormLayout()
        self.intput_2 = PyLineEdit('', '请输入页面名称')

        self.from_layout_2.addRow('页面名称：', self.intput_2)

        self.from_layout_3 = QFormLayout()
        self.intput_3 = PyLineEdit('', '请选择项目产品')

        self.from_layout_3.addRow('产品：', self.intput_3)
        self.from_layout_4 = QFormLayout()
        self.intput_4 = PyLineEdit('', '请选择产品模块')

        self.from_layout_4.addRow('模块：', self.intput_4)

        self.but_1 = PyPushButton('搜索', bg_color=THEME.blue)
        self.but_1.setMinimumHeight(30)  # 设置最小高度
        self.but_1.setMinimumWidth(50)
        self.but_2 = PyPushButton('重置', bg_color=THEME.red)
        self.but_2.setMinimumHeight(30)  # 设置最小高度
        self.but_1.setMinimumWidth(50)

        self.layout.addLayout(self.from_layout_1)
        self.layout.addLayout(self.from_layout_2)
        self.layout.addLayout(self.from_layout_3)
        self.layout.addLayout(self.from_layout_4)
        self.layout.addStretch()
        self.layout.addWidget(self.but_1)
        self.layout.addWidget(self.but_2)
        self.layout.addLayout(self.layout)


if __name__ == '__main__':
    app = QApplication()
    window = TitleWidget()
    window.show()
    app.exec()
