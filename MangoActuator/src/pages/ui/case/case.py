# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-01 下午8:57
# @Author : 毛鹏

from src.models.user_model import UserModel
from .case_dict import *
from ...parent.table import *


class CasePage(TableParent):
    def __init__(self, parent):
        super().__init__(parent,
                         search_data=search_data,
                         form_data=form_data,
                         table_column=table_column,
                         table_menu=table_menu,
                         right_data=right_data)
        self.subpage_value = 'case_steps'
        self.get = HTTP.get_case
        self.post = HTTP.post_case
        self.put = HTTP.put_case
        self._delete = HTTP.delete_case

    def run(self, row):
        user_info = UserModel()
        response_message(self, HTTP.ui_case_run(row.get("id"), user_info.selected_environment, ))

    def form_data_callback(self, obj: FormDataModel):
        if obj.key == 'case_people':
            return [ComboBoxDataModel(id=i.get('key'), name=i.get('title')) for i in obj.select().data]
        else:
            return obj.select()

    def save_callback(self, data, is_post=False):
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
