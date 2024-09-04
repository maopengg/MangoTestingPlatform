# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-08-30 14:52
# @Author : 毛鹏
from src import *
from src.models.gui_model import FromDataModel
from src.widgets import *


class DialogWidget(MangoDialog):
    clicked = Signal(object)

    def __init__(self, tips: str, from_data: list[FromDataModel], size: super = (400, 300)):
        super().__init__(tips, size)
        self.form_data = from_data
        # 创建表单布局
        form_layout = QFormLayout()
        for form in self.form_data:
            intput = MangoLineEdit(form.text, form.placeholder)
            form_layout.addRow(f"{form.title}:", intput)
            form.input = intput

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
            value = form.input.text()
            if value:
                self.data[form.key] = value
        self.accept()  # 关闭对话框
