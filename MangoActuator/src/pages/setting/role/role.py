# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-28 16:30
# @Author : 毛鹏
from src.network import Http
from .role_dict import *
from ...parent.table import TableParent


class RolePage(TableParent):
    def __init__(self, parent):
        super().__init__(parent,                          search_data=search_data,
                         form_data=form_data,
                         table_column=table_column,
                         table_menu=table_menu,
                         right_data=right_data
                         )
        self.get = Http.get_role
        self.post = Http.post_role
        self.put = Http.put_role
        self._delete = Http.delete_role
