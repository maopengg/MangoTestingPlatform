# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-09-05 16:24
# @Author : 毛鹏

from src import *
from src.models.gui_model import CascaderModel, DialogCallbackModel


class MangoCascade(QToolButton):
    clicked = Signal(object)

    style = f'''
    QToolButton {{
        background-color: {THEME.bg_one}; /* 按钮背景颜色 */
        border-radius: 5px; /* 按钮圆角半径 */
        border: 1px solid gray; /* 按钮边框样式 */
        padding: 5px; /* 按钮内边距 */
        color: black; /* 按钮字体颜色 */
    }}

    QToolButton:focus {{
        border: 1px solid {THEME.dark_four}; /* 焦点时边框颜色 */
        background-color: {THEME.bg_one}; /* 焦点时背景颜色 */
    }}

    QToolButton::menu-indicator {{
        image: url(:/icons/down.svg); /* 下拉指示器图像 */
    }}

    QMenu {{
        background-color: white; /* 菜单背景颜色 */
        border: 1px solid gray; /* 菜单边框样式 */
        padding: 0; /* 菜单内边距 */
    }}

    QMenu::item {{
        padding: 10px 15px; /* 菜单项的内边距 */
        color: black; /* 菜单项字体颜色 */
    }}

    QMenu::item:selected {{
        background-color: {THEME.dark_four}; /* 选中菜单项的背景颜色 */
        color: white; /* 选中菜单项的字体颜色 */
    }}
    '''

    def __init__(self, placeholder: str, data: list[CascaderModel], default: int = None,
                 subordinate: str | None = None, ):
        super().__init__()
        self.data: list[CascaderModel] = data
        self.subordinate: str = subordinate
        self.value: int = default

        # 创建工具按钮
        self.setPopupMode(QToolButton.InstantPopup)
        self.setStyleSheet(self.style)
        self.menu = QMenu()
        self.set_select(self.data)
        self.set_value(self.value)
        self.setMenu(self.menu)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def show_selection(self, category, value, label):
        self.setText(f'{category}/{label}')
        self.value = value
        if self.subordinate:
            self.clicked.emit(DialogCallbackModel(subordinate=self.subordinate, value=value))

    def get_value(self):
        return self.value

    def set_select(self, data: list[CascaderModel], clear: bool = False):
        if clear:
            pass
        if data:
            self.data = data
            for cascade in self.data:
                fruits_menu = QMenu(cascade.label, self)
                if cascade.children:
                    for fruit in cascade.children:
                        action = fruits_menu.addAction(fruit.label)
                        action.triggered.connect(
                            lambda checked, value=fruit.value, label=fruit.label: self.show_selection(cascade.label,
                                                                                                      value,
                                                                                                      label))
                self.menu.addMenu(fruits_menu)

    def set_value(self, value: int):
        self.value = value
        for i in self.data:
            for e in i.children:
                if e.value == value:
                    self.setText(f'{i.label}/{e.label}')
