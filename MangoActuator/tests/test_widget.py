# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-09-04 17:43
# @Author : 毛鹏
from PySide6.QtWidgets import QWidget, QVBoxLayout, QApplication, QPushButton, QFrame, QFormLayout, QLabel

from src import THEME


class Card(QFrame):
    def __init__(self, layout, background_color=THEME.pink, parent=None):
        super().__init__(parent)
        self.background_color = background_color
        self.layout = QVBoxLayout()
        self.widget = QWidget()
        self.widget.setParent(None)
        self.widget.setStyleSheet("QWidget { background-color: transparent; border: none; }")
        self.widget.setLayout(layout)
        self.layout.addWidget(self.widget)
        self.setLayout(self.layout)
        self.setFrameShape(QFrame.StyledPanel)  # 设置边框样式
        self.setFrameShadow(QFrame.Raised)  # 设置阴影样式
        self.setLineWidth(1)  # 设置边框宽度
        self.set_stylesheet()

    def set_stylesheet(self):
        style = f"""
        QFrame {{
            background-color: {self.background_color};
            border: 1px solid #d0d0d0;
            border-radius: 8px;
            padding: 10px;
        }}

        """

        self.setStyleSheet(style)


class MyQWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)  # 设置间距为0
        self.resize(800, 400)
        self.layout_1 = QFormLayout()
        self.layout_1.addWidget(QPushButton('1'))
        self.layout_1.addWidget(QLabel('哈哈哈'))
        self.widget = Card(self.layout_1)
        self.layout.addWidget(self.widget)
        self.layout.addWidget(QPushButton('2'))
        self.setLayout(self.layout)


if __name__ == '__main__':
    app = QApplication([])
    window = MyQWidget()
    window.show()
    app.exec()
