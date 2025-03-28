# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-28 16:30
# @Author : 毛鹏
from src.network import HTTP
from .page_dict import *
from ...parent.table import TableParent


class PagePage(TableParent):
    def __init__(self, parent):
        super().__init__(parent,
                         search_data=search_data,
                         form_data=form_data,
                         table_column=table_column,
                         table_menu=table_menu,
                         right_data=right_data)
        self.subpage_value = 'page_element'
        self.get = HTTP.ui.page.get_page
        self.post = HTTP.ui.page.post_page
        self.put = HTTP.ui.page.put_page
        self._delete = HTTP.ui.page.delete_page
        self.post_copy = HTTP.ui.page.page_copy
