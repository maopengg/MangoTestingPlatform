# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-10-15 14:54
# @Author : 毛鹏
from mangoui import ComboBoxDataModel, FormDataModel

from src.pages.parent.table import TableParent
from src.tools.components.message import response_message
from .tasks_dict import *


class TasksPage(TableParent):
    def __init__(self, parent):
        super().__init__(parent,
                         form_data=form_data,
                         search_data=search_data,
                         table_column=table_column,
                         table_menu=table_menu,
                         right_data=right_data)
        self.get = HTTP.system.tasks.get_tasks
        self.post = HTTP.system.tasks.post_tasks
        self.put = HTTP.system.tasks.put_tasks
        self._delete = HTTP.system.tasks.delete_tasks
        self.subpage_value = 'tasks_details'
        self.dialog_widget_size = (400, 350)

    def form_data_callback(self, data: FormDataModel):
        if data.key == 'project_product':
            return data.select()
        else:
            return [ComboBoxDataModel(id=str(i.get('key')), name=i.get('title')) for i in data.select().data]

    def run(self, row):
        response_message(self, HTTP.system.tasks.trigger_timing(row.get('id')))
