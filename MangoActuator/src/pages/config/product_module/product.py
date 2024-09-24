# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-28 16:30
# @Author : 毛鹏

from src.models.gui_model import ComboBoxDataModel, FormDataModel
from src.network import Http
from .product_dict import *
from ...parent.table import TableParent


class ProductPage(TableParent):
    def __init__(self, parent):
        super().__init__(parent, search_data, form_data, table_column, table_menu, right_data)
        self.subpage_value = 'module'
        self.get = Http.get_product
        self.post = Http.post_product
        self.put = Http.put_product
        self._delete = Http.delete_product

    def form_data_callback(self, data: FormDataModel):
        return [ComboBoxDataModel(id=i.value, name=i.label) for i in data.select()]
