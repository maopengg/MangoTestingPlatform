# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-19 11:29
# @Author : 毛鹏
from src import *


class MangoCardWidget(QWidget):
    def __init__(self, layout, title: str | None = None, background_color=THEME.dark_three, parent=None):
        super().__init__(parent)
        self.background_color = background_color
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.frame = QFrame()
        if title:
            self.frame_layout = QVBoxLayout()
            self.frame_layout.setContentsMargins(0, 0, 0, 0)
            self.frame.setLayout(self.frame_layout)
            title_label = QLabel(title)
            font = QFont()
            font.setPointSize(18)  # 设置字体大小
            font.setBold(True)  # 设置为粗体
            title_label.setFont(font)
            self.frame_layout.addWidget(title_label)
            self.frame.setLayout(self.frame_layout)
            self.frame_layout_h = QHBoxLayout()
            self.frame_layout_h.setContentsMargins(10, 0, 0, 0)
            self.frame_layout_h.addLayout(layout)
            self.frame_layout.addLayout(self.frame_layout_h)
        else:
            self.frame.setLayout(layout)
        self.layout.addWidget(self.frame)

        self.setLayout(self.layout)
        self.set_stylesheet()

    def set_stylesheet(self):
        self.setObjectName('mangoCard')
        style = f"""
        QWidget#mangoCard {{
            background-color: {self.background_color};
            border: 1px solid {self.background_color};
            border-radius: {THEME.radius}px;
            padding: 10px;
        }}
        QWidget#mangoCard > QFrame {{
            background-color: {self.background_color};
            border: 1px solid {self.background_color};
            border-radius: {THEME.radius}px;
            padding: 10px;
        }}

        """
        # QWidget#mangoCard QLabel {{
        #     border: none;
        #     margin-top: 0;
        #     margin-bottom: 0;
        #     margin-left: 0;
        #     margin-right: 5;
        #     padding-top: 0;
        #     padding-bottom: 0;
        #     padding-left: 0;
        #     padding-right: 0;
        # }}
        self.setStyleSheet(style)
