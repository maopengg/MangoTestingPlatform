# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-19 17:54
# @Author : 毛鹏
from typing import Optional

from mango_ui import *

from src.pages.parent.parent import Parent
from src.tools.methods import Methods


class SubPage(Parent):
    def __init__(self, parent, **kwargs):
        super().__init__()
        self.parent = parent
        self.page = 1
        self.page_size = 20

        self.data: dict = {}
        self.id_key: Optional[str | None] = None
        self.superior_page: Optional[str | None] = None
        self.kwargs = kwargs

        self.form_data = [FormDataModel(**i) for i in kwargs.get('form_data', [])]

        self.layout = QVBoxLayout()
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

    def show_data(self, is_refresh=False):
        if self.field_list:
            self.title_info.init(self.data, self.field_list)
        response_model = self.get(
            self.page,
            self.page_size,
            {f'{self.id_key}_id': self.data.get('id')}
        )
        self.table_widget.set_data(response_model.data, response_model.totalSize)
        if response_model.code != 200:
            response_message(self, response_model)
        return response_model

    def sub_options(self, data: DialogCallbackModel, is_refresh=True):
        if data.subordinate == 'module':
            init_data = Methods.get_product_module(self, data)
            if is_refresh:
                data.subordinate_input_object.set_select(init_data, True)
            else:
                return init_data

    def callback(self, data):
        action = data.get('action')
        if action and hasattr(self, action):
            if data.get('row'):
                getattr(self, action)(data.get('row'))
            else:
                getattr(self, action)()

    def pagination_clicked(self, data):
        if data['action'] == 'prev':
            self.page = data['page']
        elif data['action'] == 'next':
            self.page = data['page']
        elif data['action'] == 'per_page':
            self.page_size = data['page']
        self.show_data()

    def move_up(self, row):
        row1 = self.table_widget.table_widget.currentRow()
        if row1 > 0:
            self.table_widget.table_widget.data[row1], self.table_widget.table_widget.data[row1 - 1] = \
                self.table_widget.table_widget.data[row1 - 1], self.table_widget.table_widget.data[row1]
            self.table_widget.table_widget.set_value(self.table_widget.table_widget.data)
            self.update_data(self.table_widget.table_widget.data)
            self.table_widget.table_widget.setCurrentCell(row1 - 1, 0)

    def move_down(self, row):
        row1 = self.table_widget.table_widget.currentRow()

        if row1 < len(self.table_widget.table_widget.data) - 1:
            self.table_widget.table_widget.data[row1], self.table_widget.table_widget.data[row1 + 1] = \
                self.table_widget.table_widget.data[row1 + 1], self.table_widget.table_widget.data[row1]
            self.table_widget.table_widget.set_value(self.table_widget.table_widget.data)
            self.update_data(self.table_widget.table_widget.data)
            self.table_widget.table_widget.setCurrentCell(row1 + 1, 0)

    def update_data(self, data: dict):
        pass

    def back(self):
        self.parent.set_page(self.superior_page)

