# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-30 14:52
# @Author : 毛鹏

from src import *
from src.enums.gui_enum import *
from src.models.gui_model import FormDataModel, DialogCallbackModel
from src.widgets import *
from src.widgets.input.mango_combo_box import MangoComboBox


class DialogWidget(MangoDialog):
    clicked = Signal(object)

    def __init__(self, tips: str, form_data: list[FormDataModel], size: super = (400, 300)):
        super().__init__(tips, size)
        self.form_data = form_data
        # 创建表单布局
        form_layout = QFormLayout()
        for form in self.form_data:
            if callable(form.select):
                form.select = form.select()
            if form.type == InputEnum.INPUT:
                input_object = MangoLineEdit(form.placeholder, form.value, form.subordinate)
            elif form.type == InputEnum.SELECT:
                print( form.select, form.value)
                input_object = MangoComboBox(form.placeholder, form.select, form.value, form.subordinate, key=form.key)
            elif form.type == InputEnum.CASCADER:
                input_object = MangoCascade(form.placeholder, form.select, form.value, form.subordinate)
            elif form.type == InputEnum.TOGGLE:
                input_object = MangoToggle(form.value)
            else:
                raise ValueError(f'Unsupported input type: {form.type}')
            input_object.clicked.connect(self.entered)
            if form.required:
                form_layout.addRow(f"*{form.title}:", input_object)
            else:
                form_layout.addRow(f"{form.title}:", input_object)
                
            form.input_object = input_object
        main_layout = QVBoxLayout()
        main_layout.addLayout(form_layout)
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        cancel_button = MangoPushButton("取消", bg_color=THEME.bg_one)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        submit_button = MangoPushButton("提交", bg_color=THEME.blue)
        submit_button.clicked.connect(self.submit_form)
        button_layout.addWidget(submit_button)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)
        self.data = {}

    def submit_form(self):
        for form in self.form_data:
            value = form.input_object.get_value()
            if form.required:
                if value is None or value == '':
                    from src.components import error_message
                    self.data = {}
                    error_message(self, f'{form.title} 是必填项')
                    return
            if value == '':
                self.data[form.key] = None
            else:
                self.data[form.key] = value
        self.accept()  # 关闭对话框

    def entered(self, data: DialogCallbackModel):
        if isinstance(data, DialogCallbackModel):
            for i in self.form_data:
                if i.key == data.subordinate and i.key:
                    data.input_object = i.input_object
                    self.clicked.emit(data)

    def check_value(self, value):
        pass
