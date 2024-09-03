# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-08-30 14:51
# @Author : 毛鹏
from PySide6.QtWidgets import QDialog
from PySide6.QtGui import QIcon
from src.settings.settings import THEME

class MangoDialog(QDialog):
    def __init__(self, tips: str, size: super = (400, 300)):
        super().__init__()
        self.setWindowTitle(tips)
        self.setFixedSize(*size)  # 设置窗口大小
        self.setWindowIcon(QIcon(':/resource/app_icon.png'))
        # 设置样式表
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {THEME.bg_one}; /* 主体背景颜色 */
            }}
            QDialog::title {{
                background-color: {THEME.dark_one}; /* 标题栏背景颜色 */
                color: {THEME.text_title}; /* 标题栏文字颜色 */
            }}
        """)