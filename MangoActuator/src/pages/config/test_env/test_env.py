# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-28 16:30
# @Author : 毛鹏
from mango_ui import FormDataModel, ComboBoxDataModel

from .test_env_dict import *
from ...parent.table import TableParent


class TestEnvPage(TableParent):
    def __init__(self, parent):
        super().__init__(parent,
                         search_data=search_data,
                         form_data=form_data,
                         table_column=table_column,
                         table_menu=table_menu,
                         right_data=right_data)
        self.subpage_value = 'env_config'
        self.get = HTTP.get_test_object
        self.post = HTTP.post_test_object
        self.put = HTTP.put_test_object
        self._delete = HTTP.delete_test_object
        self.dialog_widget_size = (400, 350)

    def form_data_callback(self, data: FormDataModel):
        if data.key == 'project_product':
            return data.select()
        return [ComboBoxDataModel(id=str(i.get('key')), name=i.get('title')) for i in data.select().data]
