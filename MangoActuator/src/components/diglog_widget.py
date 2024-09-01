# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-08-30 14:52
# @Author : 毛鹏
from PySide6.QtWidgets import *

from src.settings.settings import THEME
from src.widgets import *


class DialogWidget(MangoDialog):
    def __init__(self, tips: str, size: super = (400, 300)):
        super().__init__(tips, size)
        # 创建表单布局
        form_layout = QFormLayout()
        self.input_1 = PyLineEdit('', '请选择项目产品')
        self.input_2 = PyLineEdit('', '请选择模块')
        self.input_3 = PyLineEdit('', '请输入页面名称')
        self.input_4 = PyLineEdit('', '请输入页面地址')
        form_layout.addRow("项目/产品:", self.input_1)
        form_layout.addRow("模块:", self.input_2)
        form_layout.addRow("页面名称:", self.input_3)
        form_layout.addRow("页面地址:", self.input_4)

        # 创建主布局
        main_layout = QVBoxLayout()
        main_layout.addLayout(form_layout)

        # 添加占位符以推送按钮到右下角
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # 添加按钮布局
        button_layout = QHBoxLayout()
        submit_button = PyPushButton("提交", bg_color=THEME.blue)
        submit_button.clicked.connect(self.submit_form)
        cancel_button = PyPushButton("取消", bg_color=THEME.bg_one)
        cancel_button.clicked.connect(self.reject)  # 关闭对话框
        button_layout.addStretch()
        # 将按钮添加到按钮布局
        button_layout.addWidget(submit_button)
        button_layout.addWidget(cancel_button)

        # 将按钮布局添加到主布局
        main_layout.addLayout(button_layout)

        # 设置主布局
        self.setLayout(main_layout)

    def submit_form(self):
        # 处理表单提交的逻辑
        print(f"字段1: {self.input_1.text()}")
        print(f"字段2: {self.input_2.text()}")
        self.accept()  # 关闭对话框
