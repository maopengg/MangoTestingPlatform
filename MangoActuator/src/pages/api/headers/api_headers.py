# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-28 16:30
# @Author : 毛鹏
from src.network import HTTP
from .api_headers_dict import *
from ...parent.table import TableParent


class ApiHeadersPage(TableParent):
    def __init__(self, parent):
        super().__init__(parent,
                         search_data=search_data,
                         form_data=form_data,
                         table_column=table_column,
                         table_menu=table_menu,
                         right_data=right_data)
        self.get = HTTP.api.headers.get_api_headers
        self.post = HTTP.api.headers.post_api_headers
        self.put = HTTP.api.headers.put_api_headers
        self._delete = HTTP.api.headers.delete_api_headers
