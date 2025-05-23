# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-10-30 15:35
# @Author : 毛鹏

from mangotools.mangos import Mango
from mangoui import *

from src.tools.components.message import response_message
from src.tools.methods import Methods


class Parent(QWidget):
    def show_data(self):
        pass

    def add(self, title='新建'):
        form_data = Mango.add_from_data(self)
        if hasattr(self, 'dialog_widget_size'):
            dialog = DialogWidget(title, form_data, self.dialog_widget_size)
        else:
            dialog = DialogWidget(title, form_data)
        dialog.clicked.connect(self.sub_options)  # type: ignore
        dialog.exec()
        if dialog.data:
            if hasattr(self, 'id_key'):
                dialog.data[self.id_key] = self.data['id']  # type: ignore
            response_model = Mango.post_save_data(self, dialog.data)
            if response_model:
                response_message(self, response_model)
            self.show_data()

    def edit(self, row, title='编辑'):
        form_data = Mango.edit_form_data(self, row, self.form_data, Methods)  # type: ignore
        if hasattr(self, 'dialog_widget_size'):
            dialog = DialogWidget(title, form_data, self.dialog_widget_size)
        else:
            dialog = DialogWidget(title, form_data)
        dialog.clicked.connect(self.sub_options)  # type: ignore
        dialog.exec()
        if dialog.data:
            response_model = Mango.put_save_data(self, row, dialog.data)
            if response_model:
                response_message(self, response_model)
            self.show_data()

    def delete(self, row):
        if hasattr(self, 'delete_callback'):
            response_model = self._delete(**self.delete_callback(row))  # type: ignore
        else:
            response_model = self._delete(row.get('id'))  # type: ignore
        response_message(self, response_model)
        self.show_data()
