# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-18 15:07
# @Author : 毛鹏
from PySide6.QtCore import QThread
from mango_ui import *

from src.pages.parent.parent import Parent
from src.tools.components.message import response_message
from src.tools.methods import Methods


class RequestThread(QThread):
    response_signal = Signal(object)

    def __init__(self, parent, page, page_size, params):
        super().__init__(parent)
        self.parent = parent
        self.page = page
        self.page_size = page_size
        self.params = params

    def run(self):
        response_model = self.parent.get(self.page, self.page_size, self.params)
        self.response_signal.emit(response_model)


class TableParent(Parent):
    def __init__(self, parent, **kwargs):
        super().__init__()
        self.parent = parent
        self.page = 1
        self.page_size = 20

        self.params = {}
        self.subpage_value = None
        self.kwargs = kwargs

        self.form_data = [FormDataModel(**i) for i in kwargs.get('form_data', [])]

        self.layout = MangoVBoxLayout(self)
        self.setLayout(self.layout)

        if kwargs.get('search_data'):
            if not isinstance(kwargs.get('search_data')[0], SearchDataModel):
                self.search_data = [SearchDataModel(**i) for i in kwargs.get('search_data', [])]
            self.titleWidget = SearchWidget(self.search_data)
            self.titleWidget.clicked.connect(self.search)
            self.layout.addWidget(self.titleWidget)
        if kwargs.get('right_data'):
            self.right_data = [RightDataModel(**i) for i in kwargs.get('right_data', [])]
            self.right_but = RightButton(self.right_data)
            self.right_but.clicked.connect(self.callback)
            self.layout.addWidget(self.right_but)
        if kwargs.get('table_column'):
            self.table_column = [TableColumnModel(**i) for i in kwargs.get('table_column', [])]
            self.table_menu = [TableMenuItemModel(**i) for i in kwargs.get('table_menu', [])]
            self.table_widget = TableList(self.table_column, self.table_menu, )
            self.table_widget.pagination.click.connect(self.pagination_clicked)
            self.table_widget.clicked.connect(self.callback)
            self.layout.addWidget(self.table_widget)

    def show_data(self):
        thread = RequestThread(self, self.page, self.page_size, self.params)
        thread.response_signal.connect(
            lambda response_model: self.table_widget.set_data(response_model.data, response_model.totalSize))
        thread.start()

    def subpage(self, row):
        self.parent.set_page(self.subpage_value, row)  # type: ignore

    def copy(self, row):
        response_message(self, self.post_copy(row.get('id')))  # type: ignore
        self.show_data()

    def callback(self, data):
        action = data.get('action')
        if action and hasattr(self, action):
            if data.get('row'):
                getattr(self, action)(row=data.get('row'))
            else:
                getattr(self, action)()

    def sub_options(self, data: DialogCallbackModel, is_refresh=True):
        if data.subordinate == 'module':
            init_data = Methods.get_product_module(self, data)
            if is_refresh:
                data.subordinate_input_object.set_select(init_data, True)
            else:
                return init_data

    def pagination_clicked(self, data):
        if data['action'] == 'prev':
            self.page = data['page']
        elif data['action'] == 'next':
            self.page = data['page']
        elif data['action'] == 'per_page':
            self.page_size = data['page']
        self.show_data()

    def search(self, data):
        if isinstance(data, dict):
            self.params = data
            self.show_data()
            success_message(self, '搜索结果展示完成~')
        else:
            self.sub_options(data)
