# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-28 16:30
# @Author : 毛鹏
from mango_ui import FormDataModel, ComboBoxDataModel

from .user_dict import *
from ...parent.table import TableParent


class UserAdministrationPage(TableParent):
    def __init__(self, parent):
        super().__init__(parent,
                         search_data=search_data,
                         form_data=form_data,
                         table_column=table_column,
                         table_menu=table_menu)
        self.get = Http.get_user_info
        self.post = Http.post_user_info
        self.put = Http.put_user_info
        self._delete = Http.delete_user_info

    def form_data_callback(self, data: FormDataModel):
        return [ComboBoxDataModel(id=i.get('key'), name=i.get('title')) for i in data.select().data]
