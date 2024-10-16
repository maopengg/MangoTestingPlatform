# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-19 17:54
# @Author : 毛鹏
import copy
import json
from typing import Optional

from mango_ui import *
from mango_ui.init import *

from src.models.network_model import ResponseModel
from src.tools.methods import Methods


class SubPage(QWidget):
    def __init__(self, parent, **kwargs):
        super().__init__()
        self.parent = parent
        self.data: dict = {}
        self.id_key: Optional[str | None] = None
        self.superior_page: Optional[str | None] = None
        self.page = 1
        self.page_size = 20
        self.kwargs = kwargs
        self.form_data = [FormDataModel(**i) for i in kwargs.get('form_data', [])]

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        if kwargs.get('right_data'):
            self.right_data = [RightDataModel(**i) for i in kwargs.get('right_data')]
            self.right_but = RightButton(self.right_data)
            self.right_but.clicked.connect(self.callback)
            self.layout.addWidget(self.right_but)
        self.field_list = [FieldListModel(**i) for i in kwargs.get('field_list', [])]
        if self.field_list:
            self.title_info = TitleInfoWidget()
            self.layout.addWidget(self.title_info)
        if kwargs.get('table_column'):
            self.table_column = [TableColumnModel(**i) for i in kwargs.get('table_column')]
            self.table_menu = [TableMenuItemModel(**i) for i in kwargs.get('table_menu')]
            self.table_widget = TableList(self.table_column, self.table_menu, )
            self.table_widget.pagination.click.connect(self.pagination_clicked)
            self.table_widget.clicked.connect(self.callback)
            self.layout.addWidget(self.table_widget)

    def show_data(self):
        if self.field_list:
            self.title_info.init(self.data, self.field_list)
        response_model: ResponseModel = self.get(
            self.page,
            self.page_size,
            {self.id_key: self.data.get('id')}
        )
        self.table_widget.set_data(response_model.data, response_model.totalSize)
        if response_model.code != 200:
            response_message(self, response_model)
        return response_model

    def callback(self, data):
        action = data.get('action')
        if action and hasattr(self, action):
            if data.get('row'):
                getattr(self, action)(data.get('row'))
            else:
                getattr(self, action)()

    def add(self):
        form_data = copy.deepcopy(self.form_data)
        for i in form_data:
            if callable(i.select):
                if hasattr(self, 'form_data_callback'):
                    i.select = self.form_data_callback(i)
                else:
                    i.select = i.select()
        dialog = DialogWidget('新建页面', form_data)
        dialog.clicked.connect(self.sub_options)
        dialog.exec()  # 显示对话框，直到关闭
        if dialog.data:
            if self.id_key:
                dialog.data[self.id_key] = self.data.get('id')
            if hasattr(self, 'form_data_callback'):
                self.save_callback(dialog.data)
            else:
                response_model: ResponseModel = self.post(dialog.data)
                response_message(self, response_model)
        self.show_data()

    def sub_options(self, data: DialogCallbackModel, is_refresh=True):
        if data.subordinate == 'module':
            init_data = Methods.get_product_module(self, data)
            if is_refresh:
                data.input_object.set_select(init_data, True)
            else:
                return init_data

    def back(self):
        self.parent.set_page(self.superior_page)

    def edit(self, row):
        form_data = copy.deepcopy(self.form_data)
        for i in form_data:
            if isinstance(row[i.key], dict):
                i.value = row[i.key].get('id', None)
            elif isinstance(row[i.key], list):
                i.value = json.dumps(row[i.key])
            else:
                i.value = row[i.key]
            if callable(i.select):
                if hasattr(self, 'form_data_callback'):
                    i.select = self.form_data_callback(i)
                else:
                    i.select = i.select()
        for i in form_data:
            if i.subordinate:
                result = next((item for item in form_data if item.key == i.subordinate), None)
                select = Methods.get_product_module_label(int(i.value))
                result.select = [ComboBoxDataModel(id=children.value, name=children.label) for children in select]
        dialog = DialogWidget('编辑页面', form_data)
        dialog.clicked.connect(self.sub_options)
        dialog.exec()  # 显示对话框，直到关闭
        if dialog.data:
            if self.id_key:
                dialog.data[self.id_key] = self.data.get('id')
            dialog.data['id'] = row['id']
            if hasattr(self, 'form_data_callback'):
                self.save_callback(dialog.data)
            else:
                response_model: ResponseModel = self.put(dialog.data)
                response_message(self, response_model)
        self.show_data()

    def delete(self, row):
        response_model: ResponseModel = self._delete(row.get('id'))
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
