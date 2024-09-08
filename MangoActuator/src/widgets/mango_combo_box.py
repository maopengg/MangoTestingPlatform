# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-09-04 17:32
# @Author : 毛鹏
from src import *

style = '''
QComboBox {{
    background-color: {_bg_color};
    border-radius: {_radius}px;
    border: {_border_size}px solid gray;
    padding-left: 10px;
    padding-right: 10px;
    selection-color: {_selection_color};
    selection-background-color: {_context_color};
    color: {_color};
}}
QComboBox:focus {{
    border: {_border_size}px solid {_context_color};
    background-color: {_bg_color_active};
}}
QComboBox::drop-down {{
    border: none;
    background-color: transparent;
    background-image: url({icon}); /* 使用背景图像 */
    background-repeat: no-repeat;
    background-position: center;
    width: 20px; /* 设置下拉按钮的宽度 */
}}
'''


class MangoComboBox(QComboBox):
    clicked = Signal(object)

    def __init__(
            self,
            placeholder: str,
            data: dict,
            default: int = None,
            subordinate: str | None = None,
            radius=8,
            border_size=1,
            color=THEME.text_foreground,
            selection_color=THEME.white,
            bg_color=THEME.white,
            bg_color_active=THEME.dark_three,
            context_color=THEME.context_color,
            icon=':/icons/down.svg'
    ):
        super().__init__()
        self.placeholder = placeholder
        self.data = data
        self.default = default
        self.subordinate = subordinate
        # 设置样式表
        self.set_stylesheet(
            radius,
            border_size,
            color,
            selection_color,
            bg_color,
            bg_color_active,
            context_color,
            icon
        )
        self.currentIndexChanged.connect(self.combo_box_changed)
        self.init_data(self.data)

        if self.placeholder:
            self.setPlaceholderText(self.placeholder)

        if self.default:
            for enum_value, option in self.data.items():
                if str(enum_value) == str(self.default):
                    self.setCurrentText(option)
                    break

    # 设置样式表的方法
    def set_stylesheet(
            self,
            radius,
            border_size,
            color,
            selection_color,
            bg_color,
            bg_color_active,
            context_color,
            icon
    ):
        # 应用样式表
        style_format = style.format(
            _radius=radius,
            _border_size=border_size,
            _color=color,
            _selection_color=selection_color,
            _bg_color=bg_color,
            _bg_color_active=bg_color_active,
            _context_color=context_color,
            icon=icon
        )
        self.setStyleSheet(style_format)
        self.setMinimumHeight(30)  # 设置最小高度

    def get_value(self):
        value = super().currentText()
        for k, v in self.data.items():
            if v == value:
                return k

    def init_data(self, data: dict, clear: bool = False):
        if clear:
            self.clear()
        if data:
            self.data = data
            self.addItems(list(data.values()))

    def combo_box_changed(self, data):
        if self.subordinate:
            self.clicked.emit({'subordinate': self.subordinate, 'value': data})