# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-28 16:30
# @Author : 毛鹏
from src.network import HTTP
from .api_info_dict import *
from ...parent.table import TableParent


class ApiInfoPage(TableParent):
    def __init__(self, parent):
        super().__init__(parent,
                         search_data=search_data,
                         form_data=form_data,
                         table_column=table_column,
                         table_menu=table_menu,
                         right_data=right_data)
        self.subpage_value = 'api_info_detailed'
        self.get = HTTP.get_api_info
        self.post = HTTP.post_api_info
        self.put = HTTP.put_api_info
        self._delete = HTTP.delete_api_info

    def run(self, row):
        print(f'点击了运行：{row}')