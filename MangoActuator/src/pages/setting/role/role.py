# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-28 16:30
# @Author : 毛鹏
from src.network import HTTP
from .role_dict import *
from ...parent.table import TableParent


class RolePage(TableParent):
    def __init__(self, parent):
        super().__init__(parent,
                         form_data=form_data,
                         table_column=table_column,
                         table_menu=table_menu,
                         right_data=right_data)
        self.get = HTTP.user.role.get_role
        self.post = HTTP.user.role.post_role
        self.put = HTTP.user.role.put_role
        self._delete = HTTP.user.role.delete_role
