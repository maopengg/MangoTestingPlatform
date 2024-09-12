# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description:
# @Time   : 2024-08-16 17:05
# @Author : 毛鹏
from src import *
from src.models.gui_model import DialogCallbackModel


class MangoLineEdit(QLineEdit):
    clicked = Signal(object)

    def __init__(
            self,
            placeholder,
            value,
            subordinate: str | None = None,
            is_password: bool = False,
            theme=THEME
    ):
        super().__init__()
        self.editingFinished.connect(self.line_edit_changed)
        self.subordinate = subordinate
        self.value = value
        self.theme = theme.model_dump()
        if is_password:
            self.setEchoMode(QLineEdit.Password)
        if placeholder:
            self.setPlaceholderText(placeholder)
        self.set_value(self.value)
        self.set_stylesheet(self.theme)

    def get_value(self):
        return self.text()

    def set_value(self, value):
        self.value = value
        if self.value is not None:
            self.setText(str(self.value))

    def line_edit_changed(self, ):
        if self.subordinate:
            self.clicked.emit(DialogCallbackModel(subordinate=self.subordinate, value=self.text()))

    def set_stylesheet(self, theme):
        style = f"""
        QLineEdit {{
        	background-color: {theme['white']};
        	border-radius: {theme['radius']}px;
        	border: {theme['border_size']}px solid gray;
        	padding-left: 10px;
            padding-right: 10px;
        	selection-color: {theme['white']};
        	selection-background-color: {theme['context_color']};
            color: {theme['text_foreground']};
        }}

        QLineEdit:focus {{
        	border: {theme['border_size']}px solid {theme['context_color']};
            background-color: {theme['dark_three']};
        }}
        """
        self.setStyleSheet(style)
        self.setMinimumHeight(30)
