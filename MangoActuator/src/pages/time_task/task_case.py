# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-10-16 17:35
# @Author : 毛鹏
from mango_ui import response_message, DialogCallbackModel, ComboBoxDataModel

from src.pages.parent.sub import SubPage
from .task_case_dict import *
from ...models.api_model import ResponseModel


class TaskCasePage(SubPage):

    def __init__(self, parent):
        super().__init__(parent,
                         table_column=table_column,
                         right_data=right_data,
                         table_menu=table_menu,
                         field_list=field_list,
                         form_data=form_data)
        self.superior_page = 'time_task'
        self.id_key = 'task'
        self.get = Http.get_tasks_list
        self.post = Http.post_tasks_list
        self.put = Http.put_tasks_list
        self._delete = Http.delete_tasks_list

    def show_data(self):
        if self.field_list:
            self.title_info.init(self.data, self.field_list)
        response_model: ResponseModel = self.get(
            self.page,
            self.page_size,
            {'task_id': self.data.get('id'), 'type': self.data.get('type')}
        )
        self.table_widget.set_data(response_model.data, response_model.totalSize)
        if response_model.code != 200:
            response_message(self, response_model)
        return response_model

    def sub_options(self, data: DialogCallbackModel, is_refresh=True):
        if data.subordinate == 'module':
            init_data = Methods.get_product_module(self, data)
            if is_refresh:
                data.input_object.set_select(init_data, True)
            else:
                return init_data
        else:
            init_data = Http.get_tasks_type_case_name(self.data.get('type'), data.value)
            if is_refresh:
                data.input_object.set_select([
                    ComboBoxDataModel(id=i.get('key'), name=i.get('title')) for i in init_data.data], True)
            else:
                return init_data

    def save_callback(self, data):
        data['sort'] = len(self.table_widget.table_widget.data)
        response_message(self, self.post(data))
