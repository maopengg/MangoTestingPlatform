# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-08-28 16:30
# @Author : 毛鹏

from src.components import *
from src.models.service_http_model import ResponseModel
from src.network.http_client import HttpClient
from src.settings.settings import THEME


class PagePage(QWidget):
    def __init__(self):
        super().__init__()
        self.page = 1
        self.page_size = 10
        self.params = {}
        self.layout = QVBoxLayout(self)
        self.titleWidget = TitleWidget()
        self.layout.addWidget(self.titleWidget)

        self.right_but = RightButton([
            {'name': '新增', 'theme': THEME.blue, 'func': self.click4},
            {'name': '批量删除', 'theme': THEME.red, 'func': self.click5}
        ])
        self.layout.addWidget(self.right_but)

        self.table_widget = TableList([
            {'key': 'id', 'name': 'ID', 'item': ''},
            {'key': 'update_time', 'name': '更新时间', 'item': ''},
            {'key': 'module', 'name': '模块名称', 'item': 'module,name'},
            {'key': 'project_product', 'name': '项目产品名称', 'item': 'project_product,name'},
            {'key': 'create_Time', 'name': '创建时间', 'item': ''},
            {'key': 'name', 'name': '页面名称', 'item': ''},
            {'key': 'url', 'name': 'URL', 'item': ''},
            {'key': 'ope', 'name': '操作', 'item': ''},
        ],
            [{'name': '编辑', 'action': 'edit'},
             {'name': '添加元素', 'action': 'add'},
             {'name': '···', 'action': '', 'son': [{'name': '复制', 'action': 'copy'},
                                                   {'name': '删除', 'action': 'delete'}]}
             ])
        self.table_widget.pagination.clicked.connect(self.pagination_clicked)
        self.table_widget.clicked.connect(self.handle_button_click)
        self.layout.addWidget(self.table_widget)
        self.setLayout(self.layout)

    def show_data(self):
        response_model: ResponseModel = HttpClient.page_list(self.page, self.page_size, self.params)
        self.table_widget.set_data(response_model.data, response_model.totalSize)

    def handle_button_click(self, data):
        action = data['action']
        row = data['row']
        if action == 'edit':
            self.click4(row)
        elif action == 'add':
            self.click4(row)
        elif action == 'more':
            self.click4(row)

    def click4(self, row):
        dialog = DialogWidget('新建页面')
        dialog.exec()  # 显示对话框，直到关闭
        for i in self.right_but.but_list:
            print(i)

    def click5(self):
        print('点击了5')

    def pagination_clicked(self, data):
        if data['action'] == 'prev':
            self.page = data['page']
        elif data['action'] == 'next':
            self.page = data['page']
        elif data['action'] == 'per_page':
            self.page_size = data['page']
        self.show_data()
