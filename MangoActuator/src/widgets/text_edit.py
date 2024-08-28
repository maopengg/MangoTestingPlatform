# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2024-08-24 17:07
# @Author : 毛鹏
import sys
from PySide6.QtWidgets import QApplication, QTextEdit


class FluentTextEdit(QTextEdit):
    def __init__(self):
        """
        构造函数，初始化文本框并设置样式表。
        """
        super().__init__()

    def setText(self, text):
        """
        设置文本框中的文本。

        参数：
        - text：要设置的文本内容。
        """
        super().setText(text)

    def text(self):
        """
        获取文本框中的文本内容。

        返回值：
        - 当前文本框中的文本。
        """
        return super().toPlainText()

    def setReadOnly(self, is_read_only):
        """
        设置文本框是否为只读状态。

        参数：
        - is_read_only：布尔值，True 表示只读，False 表示可编辑。
        """
        super().setReadOnly(is_read_only)

    def setPlaceholderText(self, text):
        """
        设置文本框的占位符文本。

        参数：
        - text：占位符文本内容。
        """
        super().setPlaceholderText(text)

    def clear(self):
        """
        清空文本框中的内容。
        """
        super().clear()

    def selectAll(self):
        """
        全选文本框中的内容。
        """
        super().selectAll()

    def copy(self):
        """
        复制选中的文本到剪贴板。
        """
        super().copy()

    def cut(self):
        """
        剪切选中的文本到剪贴板。
        """
        super().cut()

    def paste(self):
        """
        从剪贴板粘贴内容到文本框。
        """
        super().paste()

    def undo(self):
        """
        撤销上一步操作。
        """
        super().undo()

    def redo(self):
        """
        重做上一步被撤销的操作。
        """
        super().redo()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    text_edit = FluentTextEdit()
    text_edit.show()
    sys.exit(app.exec())
