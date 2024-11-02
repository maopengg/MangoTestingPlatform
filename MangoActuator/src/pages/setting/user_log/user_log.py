# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-28 16:30
# @Author : 毛鹏
from mango_ui import SearchDataModel, ComboBoxDataModel

from .user_log_dict import *
from ...parent.table import TableParent


class UserLogPage(TableParent):
    def __init__(self, parent):
        self.search_data = []
        for i in search_data:
            if i.get('key') == 'user_id':
                i['select'] = [ComboBoxDataModel(id=i.get('key'), name=i.get('title')) for i in i.get('select')().data]
            self.search_data.append(SearchDataModel(**i))
        super().__init__(parent, search_data=self.search_data, table_column=table_column, )
        self.page_size = 30
        self.get = HTTP.get_user_log
        self.post = HTTP.post_user_log
        self.put = HTTP.put_user_log
        self._delete = HTTP.delete_user_log
