# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-28 16:30
# @Author : 毛鹏
from src.network import HTTP
from src.tools.methods import Methods
from .project_dict import *
from ...parent.table import TableParent


class ProjectPage(TableParent):
    def __init__(self, parent):
        super().__init__(parent,
                         search_data=search_data,
                         form_data=form_data,
                         table_column=table_column,
                         table_menu=table_menu,
                         right_data=right_data
                         )
        self.get = HTTP.get_project
        self.post = HTTP.post_project
        self.put = HTTP.put_project
        self._delete = HTTP.delete_project

    def show_data(self, is_refresh=False):
        super().show_data()
        Methods.set_project()
