# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2024-08-24 17:07
# @Author : 毛鹏
from PySide6.QtWidgets import QLineEdit


class FluentLineEdit(QLineEdit):
    def __init__(self, parent=None):
        """
        输入框构造函数。
        """
        super().__init__(parent=parent)
        self.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 5px;
            }
            QLineEdit:hover {
                border-color: #999;
            }
            QLineEdit:focus {
                border-color: #0078D4;
            }
        """)

    def setText(self, text):
        """
        设置输入框中的文本内容。

        参数：
        - text：要设置的文本。
        """
        super().setText(text)

    def text(self):
        """
        获取输入框中的文本内容。

        返回值：
        - 当前输入框中的文本。
        """
        return super().text()

    def setReadOnly(self, is_read_only):
        """
        设置输入框是否为只读状态。

        参数：
        - is_read_only：布尔值，True 表示只读，False 表示可编辑。
        """
        super().setReadOnly(is_read_only)

    def setPlaceholderText(self, text):
        """
        设置输入框的占位符文本。

        参数：
        - text：占位符文本内容。
        """
        super().setPlaceholderText(text)

    def clear(self):
        """
        清空输入框中的内容。
        """
        super().clear()
