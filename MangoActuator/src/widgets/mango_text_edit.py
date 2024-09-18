# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-09-18 11:11
# @Author : 毛鹏
from src import *
from src.models.gui_model import DialogCallbackModel


class MangoTextEdit(QTextEdit):
    clicked = Signal(object)

    def __init__(
            self,
            placeholder,
            value,
            theme=THEME
    ):
        super().__init__()
        self.value = value
        self.theme = theme.model_dump()

        if placeholder:
            self.setPlaceholderText(placeholder)
        self.set_stylesheet(self.theme)

    def set_stylesheet(self, theme):
        style = f"""
        QTextEdit {{
        	background-color: {theme['white']};
        	border-radius: {theme['radius']}px;
        	border: {theme['border_size']}px solid gray;
        	padding-left: 10px;
            padding-right: 10px;
        	selection-color: {theme['white']};
        	selection-background-color: {theme['context_color']};
            color: {theme['text_foreground']};
        }}

        QTextEdit:focus {{
        	border: {theme['border_size']}px solid {theme['context_color']};
            background-color: {theme['dark_three']};
        }}
        """
        self.setStyleSheet(style)
