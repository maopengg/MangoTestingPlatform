# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-28 16:30
# @Author : 毛鹏
from src.network import HTTP
from .user_log_dict import *
from ...parent.table import TableParent


class UserLogPage(TableParent):
    def __init__(self, parent):
        super().__init__(parent, search_data=search_data, table_column=table_column, )
        self.page_size = 30
        self.get = HTTP.get_user_log
        self.post = HTTP.post_user_log
        self.put = HTTP.put_user_log
        self._delete = HTTP.delete_user_log
