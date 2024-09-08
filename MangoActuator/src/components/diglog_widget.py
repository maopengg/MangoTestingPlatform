# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-08-30 14:52
# @Author : 毛鹏
from src import *
from src.enums.gui_enum import *
from src.models.gui_model import FormDataModel, DialogCallbackModel
from src.widgets import *
from src.widgets.mango_combo_box import MangoComboBox


class DialogWidget(MangoDialog):
    clicked = Signal(object)

    def __init__(self, tips: str, form_data: list[FormDataModel], size: super = (400, 300)):
        super().__init__(tips, size)
        self.form_data = form_data
        # 创建表单布局
        form_layout = QFormLayout()
        for form in self.form_data:
            if form.type == InputEnum.INPUT:
                input_object = MangoLineEdit(form.value, form.placeholder, form.subordinate)
            elif form.type == InputEnum.SELECT:
                input_object = MangoComboBox(form.placeholder, form.select, form.value, form.subordinate)
            elif form.type == InputEnum.CASCADER:
                input_object = MangoCascade(form.placeholder, form.select, form.value, form.subordinate)
            else:
                raise ValueError(f'Unsupported input type: {form.type}')
            input_object.clicked.connect(self.entered)
            if form.required:
                form_layout.addRow(f"*{form.title}:", input_object)
            else:
                form_layout.addRow(f"{form.title}:", input_object)
            form.input_object = input_object
        # 创建主布局
        main_layout = QVBoxLayout()
        main_layout.addLayout(form_layout)

        # 添加占位符以推送按钮到右下角
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # 添加按钮布局
        button_layout = QHBoxLayout()
        submit_button = MangoPushButton("提交", bg_color=THEME.blue)
        submit_button.clicked.connect(self.submit_form)
        cancel_button = MangoPushButton("取消", bg_color=THEME.bg_one)
        cancel_button.clicked.connect(self.reject)  # 关闭对话框
        button_layout.addStretch()
        # 将按钮添加到按钮布局
        button_layout.addWidget(submit_button)
        button_layout.addWidget(cancel_button)

        # 将按钮布局添加到主布局
        main_layout.addLayout(button_layout)

        # 设置主布局
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
        for i in self.form_data:
            if i.key == data.subordinate and i.key:
                data.key = i.key
                data.input_object = i.input_object
                self.clicked.emit(data)

    def check_value(self, value):
        pass
