# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-19 17:54
# @Author : 毛鹏
import copy

from PySide6.QtWidgets import QWidget, QVBoxLayout

from src.components import *
from src.components.message import response_message
from src.components.title_info import TitleInfoWidget
from src.models.gui_model import *
from src.models.network_model import ResponseModel
from src.network import Http


class SubPage(QWidget):
    def __init__(self, parent, custom_page=False, **kwargs):
        super().__init__()
        self.parent = parent

        self.data: dict = {}
        self.id_key = ''
        self.page_id = None
        self.page = 1
        self.page_size = 10
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.setContentsMargins(0, 0, 0, 0)

        if not custom_page:
            self.table_column = [TableColumnModel(**i) for i in kwargs.get('table_column')]
            self.table_menu = [TableMenuItemModel(**i) for i in kwargs.get('table_menu')]
            self.field_list = [FieldListModel(**i) for i in kwargs.get('field_list')]
            self.form_data = [FormDataModel(**i) for i in kwargs.get('form_data')]
            self.right_data = [RightDataModel(**i) for i in kwargs.get('right_data')]

            self.right_but = RightButton(self.right_data)
            self.right_but.clicked.connect(self.callback)
            self.layout.addWidget(self.right_but)

            self.title_info = TitleInfoWidget()
            self.layout.addWidget(self.title_info)

            self.table_widget = TableList(self.table_column, self.table_menu, )
            self.table_widget.pagination.clicked.connect(self.pagination_clicked)
            self.table_widget.clicked.connect(self.callback)
            self.layout.addWidget(self.table_widget)

    def show_data(self):
        self.title_info.init(self.data, self.field_list)
        response_model: ResponseModel = self.get(
            self.page,
            self.page_size,
            {self.id_key: self.data.get('id')}
        )
        self.table_widget.set_data(response_model.data, response_model.totalSize)
        if response_model.code != 200:
            response_message(self, response_model)

    def callback(self, data):
        if data.get('row'):
            getattr(self, data['action'])(data.get('row'))
        else:
            getattr(self, data['action'])()

    def add(self):
        form_data = copy.deepcopy(self.form_data)
        dialog = DialogWidget('新建页面', form_data)
        dialog.exec()  # 显示对话框，直到关闭
        if dialog.data:
            dialog.data['page'] = self.page_id
            response_model: ResponseModel = Http.post_page_element(dialog.data)
            response_message(self, response_model)
        self.show_data()

    def back(self):
        self.parent.set_page(self.superior_page)

    def edit(self, row):
        form_data = copy.deepcopy(self.form_data)
        for i in form_data:
            if isinstance(row[i.key], dict):
                i.value = row[i.key].get('id', None)
            else:
                i.value = row[i.key]
        dialog = DialogWidget('编辑页面', form_data)
        dialog.exec()  # 显示对话框，直到关闭
        if dialog.data:
            dialog.data['page'] = self.page_id
            dialog.data['id'] = row['id']
            response_model: ResponseModel = Http.put_page_element(dialog.data)
            response_message(self, response_model)
        self.show_data()

    def delete(self, row):
        response_model: ResponseModel = Http.delete_page_element(row.get('id'))
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
