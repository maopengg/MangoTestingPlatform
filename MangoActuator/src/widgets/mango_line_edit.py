# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description:
# @Time   : 2024-08-16 17:05
# @Author : 毛鹏
from src import *

style = '''
QLineEdit {{
	background-color: {_bg_color};
	border-radius: {_radius}px;
	border: {_border_size}px solid gray;
	padding-left: 10px;
    padding-right: 10px;
	selection-color: {_selection_color};
	selection-background-color: {_context_color};
    color: {_color};
}}
QLineEdit:focus {{
	border: {_border_size}px solid {_context_color};
    background-color: {_bg_color_active};
}}
'''


# PY PUSH BUTTON

class MangoLineEdit(QLineEdit):
    clicked = Signal(object)

    def __init__(
            self,
            text,
            place_holder_text,
            subordinate: str | None = None,
            is_password: bool = False,
            radius=8,
            border_size=1,
            color=THEME.text_foreground,
            selection_color=THEME.white,
            bg_color=THEME.white,
            bg_color_active=THEME.dark_three,
            context_color=THEME.context_color
    ):
        super().__init__()
        self.editingFinished.connect(self.line_edit_changed)
        self.subordinate = subordinate
        # PARAMETERS
        if text:
            self.setText(text)
        if is_password:
            self.setEchoMode(QLineEdit.Password)
        if place_holder_text:
            self.setPlaceholderText(place_holder_text)

        # SET STYLESHEET
        self.set_stylesheet(
            radius,
            border_size,
            color,
            selection_color,
            bg_color,
            bg_color_active,
            context_color
        )

    # SET STYLESHEET
    def set_stylesheet(
            self,
            radius,
            border_size,
            color,
            selection_color,
            bg_color,
            bg_color_active,
            context_color
    ):
        # APPLY STYLESHEET
        style_format = style.format(
            _radius=radius,
            _border_size=border_size,
            _color=color,
            _selection_color=selection_color,
            _bg_color=bg_color,
            _bg_color_active=bg_color_active,
            _context_color=context_color
        )
        self.setStyleSheet(style_format)
        self.setMinimumHeight(30)  # 设置最小高度

    def get_value(self):
        return self.text()

    def line_edit_changed(self, ):
        if self.subordinate:
            self.clicked.emit({'subordinate': self.subordinate, 'value': self.text()})
