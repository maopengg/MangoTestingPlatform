# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-10-15 14:54
# @Author : 毛鹏
from mango_ui import ComboBoxDataModel, FormDataModel, response_message

from src.pages.parent.table import TableParent
from .scheduled_task_dict import *


class ScheduledTaskPage(TableParent):
    def __init__(self, parent):
        super().__init__(parent,
                         form_data=form_data,
                         search_data=search_data,
                         table_column=table_column,
                         table_menu=table_menu,
                         right_data=right_data)
        self.get = HTTP.get_scheduled_tasks
        self.post = HTTP.post_scheduled_tasks
        self.put = HTTP.put_scheduled_tasks
        self._delete = HTTP.delete_scheduled_tasks
        self.subpage_value = 'task_case'
        self.dialog_widget_size = (400, 350)

    def form_data_callback(self, data: FormDataModel):
        if data.key == 'project_product':
            return data.select()
        else:
            return [ComboBoxDataModel(id=str(i.get('key')), name=i.get('title')) for i in data.select().data]

    def run(self, row):
        response_message(self, HTTP.get_run_scheduled_tasks(row.get('id')))
