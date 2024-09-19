# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-08-28 16:30
# @Author : 毛鹏
from src.network import Http
from .page_dict import *
from ...parent.table import TableParent


class PagePage(TableParent):
    def __init__(self, parent):
        super().__init__(parent, search_data, form_data, table_column, table_menu, right_data)
        self.subpage_value = 'page_element'
        self.get = Http.get_page
        self.post = Http.post_page
        self.put = Http.put_page
        self._delete = Http.delete_page
