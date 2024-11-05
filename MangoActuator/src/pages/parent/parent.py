# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-10-30 15:35
# @Author : 毛鹏

from mango_ui import *
from mangokit import Mango

from src.tools.methods import Methods


class Parent(QWidget):
    def show_data(self, is_refresh=False):
        pass

    def add(self, title='新建'):
        form_data = Mango.add_from_data(self)
        dialog = DialogWidget(title, form_data)
        dialog.clicked.connect(self.sub_options)
        dialog.exec()
        if dialog.data:
            if hasattr(self, 'id_key'):
                dialog.data[self.id_key] = self.data['id']
            response_model = Mango.post_save_data(self, dialog.data)
            if response_model:
                response_message(self, response_model)
            self.show_data()

    def edit(self, row, title='编辑'):
        form_data = Mango.edit_form_data(self, row, self.form_data, Methods)
        dialog = DialogWidget(title, form_data)
        dialog.clicked.connect(self.sub_options)
        dialog.exec()
        if dialog.data:
            response_model = Mango.put_save_data(self, row, dialog.data)
            if response_model:
                response_message(self, response_model)
            self.show_data()

    def delete(self, row):
        response_model = self._delete(row.get('id'))
        response_message(self, response_model)
        self.show_data()
