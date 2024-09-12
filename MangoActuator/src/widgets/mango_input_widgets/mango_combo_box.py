# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-09-04 17:32
# @Author : 毛鹏
from src import *
from src.models.gui_model import DialogCallbackModel, ComboBoxDataModel


class MangoComboBox(QComboBox):
    clicked = Signal(object)

    def __init__(
            self,
            placeholder: str,
            data: list[ComboBoxDataModel],
            value: int = None,
            subordinate: str | None = None,
            theme: ThemeConfig = THEME,
    ):
        super().__init__()
        self.placeholder = placeholder
        self.data = data
        self.value = value
        self.subordinate = subordinate
        self.theme = theme.model_dump()
        # 设置样式表
        self.set_stylesheet(self.theme)
        self.currentIndexChanged.connect(self.combo_box_changed)
        self.set_select(self.data)
        self.setCurrentIndex(-1)
        self.set_value(self.value)
        if self.placeholder:
            self.setPlaceholderText(self.placeholder)

    # 设置样式表的方法

    def get_value(self):
        value = self.currentText()
        for i in self.data:
            if i.name == value:
                return i.id

    def set_select(self, data: list[ComboBoxDataModel], clear: bool = False):
        if clear:
            self.clear()
        if data:
            self.data = data
            self.addItems([i.name for i in data])

    def set_value(self, value: int):
        self.value = value
        if value is not None:
            for i in self.data:
                if i.id == value:
                    self.setCurrentText(i.name)
                    break
                else:
                    self.setCurrentText('')

    def combo_box_changed(self, data):
        if self.subordinate:
            self.clicked.emit(DialogCallbackModel(subordinate=self.subordinate, value=data))

    def set_stylesheet(self, style_config: dict, icon=':/icons/down.svg'):

        style = f'''
        QComboBox {{
            background-color: {style_config['white']};
            border-radius: {style_config['radius']}px;
            border: {style_config['border_size']}px solid gray;
            padding-left: 10px;
            padding-right: 10px;
            selection-color: {style_config['white']};
            selection-background-color: {style_config['context_color']};
            color: {style_config['text_foreground']};
        }}
        QComboBox:focus {{
            border: {style_config['border_size']}px solid {style_config['context_color']};
            background-color: {style_config['dark_three']};
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
        self.setStyleSheet(style)
        self.setMinimumHeight(30)  # 设置最小高度
