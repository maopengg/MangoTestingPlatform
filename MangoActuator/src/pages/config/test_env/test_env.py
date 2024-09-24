# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-28 16:30
# @Author : 毛鹏
from src.models.gui_model import FormDataModel, ComboBoxDataModel
from src.network import Http
from .test_env_dict import *
from ...parent.table import TableParent


class TestEnvPage(TableParent):
    def __init__(self, parent):
        super().__init__(parent, search_data, form_data, table_column, table_menu, right_data)
        self.subpage_value = 'database'
        self.get = Http.get_test_object
        self.post = Http.post_test_object
        self.put = Http.put_test_object
        self._delete = Http.delete_test_object

    def form_data_callback(self, data: FormDataModel):
        if data.key == 'project_product':
            return data.select()
        return [ComboBoxDataModel(id=i.get('key'), name=i.get('title')) for i in data.select().data]