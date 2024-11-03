# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-10-15 14:54
# @Author : 毛鹏
from mango_ui import ComboBoxDataModel, FormDataModel, response_message

from src.network import HTTP
from .time_strategy_dict import *
from src.pages.parent.table import TableParent


class TimePage(TableParent):
    def __init__(self, parent):
        super().__init__(parent,
                         form_data=form_data,
                         search_data=search_data,
                         table_column=table_column,
                         table_menu=table_menu,
                         right_data=right_data)
        self.get = HTTP.get_time_tasks
        self.post = HTTP.post_time_tasks
        self.put = HTTP.put_time_tasks
        self._delete = HTTP.delete_time_tasks
