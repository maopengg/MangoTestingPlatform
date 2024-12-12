# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-28 16:30
# @Author : 毛鹏
from src.network import HTTP
from .public_dict import *
from ...parent.table import TableParent


class PublicPage(TableParent):
    def __init__(self, parent):
        super().__init__(parent,
                         search_data=search_data,
                         form_data=form_data,
                         table_column=table_column,
                         table_menu=table_menu,
                         right_data=right_data)
        self.get = HTTP.ui.public.get_public
        self.post = HTTP.ui.public.post_public
        self.put = HTTP.ui.public.put_public
        self._delete = HTTP.ui.public.delete_public
