# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-01 下午8:57
# @Author : 毛鹏
from src.models.socket_model import ResponseModel
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
        self.get = HTTP.ui.case.get_case
        self.post = HTTP.ui.case.post_case
        self.put = HTTP.ui.case.put_case
        self._delete = HTTP.ui.case.delete_case
        self.post_copy = HTTP.ui.case.copy_case

    def run(self, row):
        user_info = UserModel()
        if user_info.selected_environment is None:
            error_message(self, '请先在右上角选择测试环境后再开始测试！')
            return
        response_message(self, HTTP.ui.case.ui_test_case(row.get("id"), user_info.selected_environment, ))

    def batch_run(self):
        case_id_list = self.table_widget.table_widget.get_selected_items()
        if not case_id_list:
            error_message(self, '请按住shift然后使用鼠标在表格进行多选，然后再点击批量执行')
            return
        user_info = UserModel()
        response_message(self, HTTP.ui.case.ui_test_case_batch(case_id_list, user_info.selected_environment, ))

    def form_data_callback(self, obj: FormDataModel):
        if obj.key == 'case_people':
            return [ComboBoxDataModel(id=str(i.get('key')), name=i.get('title')) for i in obj.select().data]
        else:
            return obj.select()

    def save_callback(self, data, is_post=False):
        if data.get('front_custom') is None:
            data['front_custom'] = []
        if data.get('front_sql') is None:
            data['front_sql'] = []
        if data.get('posterior_sql') is None:
            data['posterior_sql'] = []
        data['status'] = TaskEnum.STAY_BEGIN.value
        if is_post:
            response_model: ResponseModel = self.post(data)
        else:
            response_model: ResponseModel = self.put(data)
        response_message(self, response_model)
