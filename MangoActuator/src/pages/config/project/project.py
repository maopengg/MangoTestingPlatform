# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-28 16:30
# @Author : 毛鹏
from src.network import Http
from .project_dict import *
from ...parent.table import TableParent


class ProjectPage(TableParent):
    def __init__(self, parent):
        super().__init__(parent, search_data, form_data, table_column, table_menu, right_data)
        self.get = Http.get_project
        self.post = Http.post_project
        self.put = Http.put_project
        self._delete = Http.delete_project
