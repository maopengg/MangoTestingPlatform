# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2024-09-01 下午9:01
# @Author : 毛鹏
import copy

from PySide6.QtWidgets import QWidget, QVBoxLayout

from src.components import *
from src.components.message import response_message
from src.components.title_info import TitleInfoWidget
from src.models.network_model import ResponseModel
from src.network.http_ui import HttpUi
from src.settings.settings import THEME


class PageElementPage(QWidget):
    table_column = [
        {'key': 'name', 'name': '元素名称', 'item': ''},
        {'key': 'exp', 'name': '表达式类型', 'item': ''},
        {'key': 'loc', 'name': '定位表达式', 'item': ''},
        {'key': 'is_iframe', 'name': '是否在iframe中', 'item': ''},
        {'key': 'sleep', 'name': '等待时间（秒）', 'item': ''},
        {'key': 'sub', 'name': '元素下标（1开始）', 'item': ''},
        {'key': 'ope', 'name': '操作', 'item': ''},
    ]
    table_menu = [
        {'name': '调试', 'action': 'debug'},
        {'name': '编辑', 'action': 'edit'},
        {'name': '删除', 'action': 'delete'}
    ]
    field_list = [
        {'key': 'id', 'name': '页面ID'}, {'key': 'url', 'name': '页面地址'}, {'key': 'name', 'name': '页面名称'},
    ]
    from_data = [
        {'title': '元素名称', 'place_holder_text': '请输入元素名称', 'key': 'name', 'intput': None,
         'text': None},
        {'title': '表达式类型', 'place_holder_text': '请选择元素表达式类型', 'key': 'exp', 'intput': None,
         'text': None},
        {'title': '元素表达式', 'place_holder_text': '元素表达式', 'key': 'loc', 'intput': None, 'text': None},
        {'title': '等待时间', 'place_holder_text': '请输入元素等待时间', 'key': 'sleep', 'intput': None, 'text': None},
        {'title': '元素下标', 'place_holder_text': '请输入元素下标', 'key': 'sub', 'intput': None, 'text': None}
    ]

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.data: dict = {}
        self.page = 1
        self.page_size = 10

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.title_info = TitleInfoWidget()
        self.layout.addWidget(self.title_info)

        self.right_data = [
            {'name': '新增', 'theme': THEME.blue, 'func': self.add},
            {'name': '返回', 'theme': THEME.orange, 'func': self.back}
        ]
        self.right_but = RightButton(self.right_data)
        self.layout.addWidget(self.right_but)

        self.table_widget = TableList(self.table_column, self.table_menu, )
        self.table_widget.pagination.clicked.connect(self.pagination_clicked)
        self.table_widget.clicked.connect(self.handle_button_click)
        self.layout.addWidget(self.table_widget)

    def show_data(self, is_refresh=False):
        self.title_info.init(self.data, self.field_list)
        response_model: ResponseModel = HttpUi.get_page_element(self.page, self.page_size,
                                                                {'page_id': self.data.get('id')})
        self.table_widget.set_data(response_model.data, response_model.totalSize)
        if is_refresh:
            response_message(self, response_model)

    def handle_button_click(self, data):
        action = data['action']
        row = data['row']
        if action == 'edit':
            self.edit(row)
        elif action == 'delete':
            self.delete(row)

    def add(self, row):
        from_data = copy.deepcopy(self.from_data)
        dialog = DialogWidget('新建页面', from_data)
        dialog.exec()  # 显示对话框，直到关闭
        if dialog.data:
            response_model: ResponseModel = HttpUi.post_page_element(dialog.data)
            response_message(self, response_model)
        self.show_data()

    def back(self, row):
        self.parent.set_page('page', row)

    def edit(self, row):
        from_data = copy.deepcopy(self.from_data)
        for i in from_data:
            if isinstance(row[i['key']], dict):
                i['text'] = row[i['key']]['name']
            else:
                i['text'] = row[i['key']]
        dialog = DialogWidget('编辑页面', from_data)
        dialog.exec()  # 显示对话框，直到关闭
        if dialog.data:
            data = dialog.data
            data['id'] = row['id']
            response_model: ResponseModel = HttpUi.put_page_element(data)
            response_message(self, response_model)
        self.show_data()

    def delete(self, row):
        response_model: ResponseModel = HttpUi.delete_page_element(row.get('id'))
        response_message(self, response_model)
        self.show_data()

    def pagination_clicked(self, data):
        if data['action'] == 'prev':
            self.page = data['page']
        elif data['action'] == 'next':
            self.page = data['page']
        elif data['action'] == 'per_page':
            self.page_size = data['page']
        self.show_data()

    def search(self, data):
        self.params = data
        self.show_data(True)
