# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-01 下午9:01
# @Author : 毛鹏

from src.network import HTTP
from src.pages.parent.sub import SubPage
from src.tools.methods import Methods
from .module_dict import *


class ModulePage(SubPage):

    def __init__(self, parent):
        super().__init__(parent,
                         table_column=table_column,
                         right_data=right_data,
                         table_menu=table_menu,
                         field_list=field_list,
                         form_data=form_data)
        self.superior_page = 'product'
        self.id_key = 'project_product'
        self.get = HTTP.get_module
        self.post = HTTP.post_module
        self.put = HTTP.put_module
        self._delete = HTTP.delete_module

    def show_data(self, is_refresh=False):
        super().show_data()
        Methods.set_project()
