# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2024-08-24 17:08
# @Author : 毛鹏
from src import *


class MangoLabel(QLabel):
    def __init__(self, text=None, parent=None):
        """
        标签构造函数。

        参数：
        - text：标签显示的文本。
        """
        super().__init__(text, parent)

    def setText(self, text):
        """
        设置标签的文本内容。

        参数：
        - text：要设置的文本。
        """
        super().setText(text)

    def text(self):
        """
        获取标签的文本内容。

        返回值：
        - 当前标签的文本。
        """
        return super().text()
