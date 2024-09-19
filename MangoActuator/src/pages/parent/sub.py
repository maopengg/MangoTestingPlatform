# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-19 17:54
# @Author : 毛鹏
import copy

from src import *
from src.components import *
from src.models.gui_model import *
from src.models.network_model import ResponseModel


class SubPage(QWidget):
    def __init__(self, parent, *args, **kwargs):
        super().__init__()
        self.parent = parent

        self.data: dict = {}
        self.id_key = ''
        self.page_id = None
        self.page = 1
        self.page_size = 10

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

    def show_data(self, is_refresh=False):
        response_model: ResponseModel = self.get(
            self.page,
            self.page_size,
            {self.id_key: self.data.get('id')}
        )
        return response_model

    def sub_options(self, data: DialogCallbackModel, is_refresh=True):
        if data.key == 'module':
            init_data = set_product_module(self, data)
            if is_refresh:
                data.input_object.set_select(init_data, True)
            else:
                return init_data

    def add(self):
        form_data = copy.deepcopy(self.form_data)
        dialog = DialogWidget('新建页面', form_data)
        dialog.clicked.connect(self.sub_options)
        dialog.exec()  # 显示对话框，直到关闭
        if dialog.data:
            response_model: ResponseModel = self.post(dialog.data)
            response_message(self, response_model)
            self.show_data()

    def edit(self, row):
        form_data = copy.deepcopy(self.form_data)
        for i in form_data:
            if isinstance(row[i.key], dict):
                i.value = row[i.key].get('id', None)
            else:
                i.value = row[i.key]
        for i in form_data:
            if i.subordinate:
                result = next((item for item in form_data if item.key == i.subordinate), None)
                select = get_product_module_label(int(i.value))
                result.select = [ComboBoxDataModel(id=children.value, name=children.label) for children in select]
        dialog = DialogWidget('编辑页面', form_data, )
        dialog.exec()  # 显示对话框，直到关闭
        if dialog.data:
            data = dialog.data
            data['id'] = row['id']
            response_model: ResponseModel = self.put(data)
            response_message(self, response_model)
            self.show_data()

    def subpage(self, row):
        self.parent.set_page(self.subpage_value, row)

    def copy(self, row):
        print('点击了复制', row)

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

    def search(self, data):
        self.params = data
        self.show_data(True)
