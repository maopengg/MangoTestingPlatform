# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-10-16 17:35
# @Author : 毛鹏
from mango_ui import DialogCallbackModel, ComboBoxDataModel, FormDataModel

from src.models.socket_model import ResponseModel
from src.network import HTTP
from src.pages.parent.sub import SubPage
from src.tools.components.message import response_message
from .tasks_details_dict import *


class TasksDetailsPage(SubPage):

    def __init__(self, parent):
        super().__init__(parent,
                         table_column=table_column,
                         right_data=right_data,
                         table_menu=table_menu,
                         field_list=field_list,
                         form_data=form_data)
        self.superior_page = 'scheduled_task'
        self.id_key = 'task'
        self.get = HTTP.system.tasks_details.get_tasks_list
        self.post = HTTP.system.tasks_details.post_tasks_list
        self.put = HTTP.system.tasks_details.put_tasks_list
        self._delete = HTTP.system.tasks_details.delete_tasks_list

    def show_data(self, is_refresh=False):
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

    def form_data_callback(self, data: FormDataModel):
        if data.key == 'module':
            return data.select(self.data.get('project_product').get('id'))

    def sub_options(self, data: DialogCallbackModel, is_refresh=True):
        if data.subordinate == 'case_id':
            init_data = HTTP.system.tasks_details.get_type_case_name(self.data.get('type'), data.value)
            if is_refresh:
                data.subordinate_input_object.set_select([
                    ComboBoxDataModel(id=str(i.get('key')), name=i.get('title')) for i in init_data.data], True)
            else:
                return init_data

    def save_callback(self, data: dict, is_post: bool = False):
        data['sort'] = len(self.table_widget.table_widget.data)
        response_message(self, self.post(data))
