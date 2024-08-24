# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2024-08-24 16:48
# @Author : 毛鹏
from PySide6.QtWidgets import QWidget, QVBoxLayout
import sys
from PySide6.QtWidgets import QApplication
from src.widgets.label import FluentLabel
from  src.widgets.line_edit import FluentLineEdit
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("example")
        layout = QVBoxLayout()

        button1 = FluentLabel('以下是使用 PySide6 实现的标签组件和输入框组件：')
        button2 = FluentLineEdit()

        layout.addWidget(button1)
        layout.addWidget(button2)

        self.setLayout(layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
