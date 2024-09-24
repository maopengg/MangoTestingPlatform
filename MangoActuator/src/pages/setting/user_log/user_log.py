# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-28 16:30
# @Author : 毛鹏
from src.network import Http
from .user_log_dict import *
from ...parent.table import TableParent


class UserLogPage(TableParent):
    def __init__(self, parent):
        super().__init__(parent, search_data, form_data, table_column, table_menu, right_data)
        self.subpage_value = 'page_element'
        self.get = Http.get_user_log
        self.post = Http.post_user_log
        self.put = Http.put_user_log
        self._delete = Http.delete_user_log
