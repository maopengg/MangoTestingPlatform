# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-28 16:30
# @Author : 毛鹏
from mango_ui import ComboBoxDataModel, FormDataModel, response_message

from src.enums.tools_enum import StatusEnum
from src.models.network_model import ResponseModel
from src.models.user_model import UserModel
from .case_dict import *
from ...parent.table import TableParent


class ApiCasePage(TableParent):
    def __init__(self, parent):
        super().__init__(parent,
                         search_data=search_data,
                         form_data=form_data,
                         table_column=table_column,
                         table_menu=table_menu,
                         right_data=right_data)
        self.subpage_value = 'api_case_detailed'
        self.get = HTTP.get_api_case
        self.post = HTTP.post_api_case
        self.put = HTTP.put_api_case
        self._delete = HTTP.delete_api_case

    def form_data_callback(self, obj: FormDataModel):
        if obj.key == 'case_people':
            return [ComboBoxDataModel(id=i.get('key'), name=i.get('title')) for i in obj.select().data]
        else:
            return obj.select()

    def save_callback(self, data, is_post=False):
        data['status'] = StatusEnum.FAIL.value
        if data.get('front_custom') is None:
            data['front_custom'] = []
        if data.get('front_sql') is None:
            data['front_sql'] = []
        if data.get('posterior_sql') is None:
            data['posterior_sql'] = []
        if is_post:
            response_model: ResponseModel = self.post(data)
        else:
            response_model: ResponseModel = self.put(data)
        response_message(self, response_model)

    def run(self, row):
        user_info = UserModel()
        response_message(self, HTTP.get_api_case_run(row.get("id"), user_info.selected_environment, ))
