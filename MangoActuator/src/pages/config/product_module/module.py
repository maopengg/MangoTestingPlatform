# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-01 下午9:01
# @Author : 毛鹏

from src.network import Http
from src.pages.parent.sub import SubPage
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
        self.get = Http.get_module
        self.post = Http.post_module
        self.put = Http.put_module
        self._delete = Http.delete_module
