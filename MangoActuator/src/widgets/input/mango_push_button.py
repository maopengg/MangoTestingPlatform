# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-08-16 17:05
# @Author : 毛鹏
from src import *

style = '''
QPushButton {{
	border: 1px solid {border};
    color: {_color};
	border-radius: {_radius};	
	background-color: {_bg_color};
}}
QPushButton:hover {{
	background-color: {_bg_color_hover};
}}
QPushButton:pressed {{	
	background-color: {_bg_color_pressed};
}}
'''


# PY PUSH BUTTON

class MangoPushButton(QPushButton):
    def __init__(
            self,
            text,
            radius=8,
            parent=None,
            color=THEME.text_foreground,
            bg_color=THEME.dark_one,
            bg_color_hover=THEME.dark_three,
            bg_color_pressed=THEME.dark_four
    ):
        super().__init__()

        self.setText(text)
        if parent != None:
            self.setParent(parent)
        self.setCursor(Qt.PointingHandCursor)

        custom_style = style.format(
            border=THEME.dark_four,
            _color=color,
            _radius=radius,
            _bg_color=bg_color,
            _bg_color_hover=bg_color_hover,
            _bg_color_pressed=bg_color_pressed
        )
        self.setStyleSheet(custom_style)
        self.setMinimumHeight(35)
        self.setMinimumWidth(60)
