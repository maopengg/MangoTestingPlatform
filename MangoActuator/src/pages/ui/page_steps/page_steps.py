# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-28 16:30
# @Author : 毛鹏
from src.models.socket_model import ResponseModel
from src.models.user_model import UserModel
from src.network import HTTP
from .page_steps_dict import *
from ...parent.table import *


class PageStepsPage(TableParent):
    def __init__(self, parent):
        super().__init__(parent,
                         search_data=search_data,
                         form_data=form_data,
                         table_column=table_column,
                         table_menu=table_menu,
                         right_data=right_data)
        self.subpage_value = 'page_steps_detailed'
        self.get = HTTP.ui.page_steps.get_page_steps
        self.post = HTTP.ui.page_steps.post_page_steps
        self.put = HTTP.ui.page_steps.put_page_steps
        self._delete = HTTP.ui.page_steps.delete_page_steps
        self.post_copy = HTTP.ui.page_steps.copy_page_steps

    def sub_options(self, data: DialogCallbackModel, is_refresh=True):
        init_data = None
        if data.subordinate == 'module':
            init_data = Methods.get_product_module(self, data)
        elif data.subordinate == 'page':
            response_model: ResponseModel = HTTP.ui.page.module_page_name(data.value)
            init_data = [ComboBoxDataModel(id=str(i.get('key')), name=i.get('title')) for i in response_model.data]
        if is_refresh and init_data:
            data.subordinate_input_object.set_select(init_data, True)
        else:
            return init_data

    def subordinate_callback(self, data: FormDataModel):
        if data.subordinate == 'page':
            response_model: ResponseModel = HTTP.ui.page.module_page_name(data.value)
            return [ComboBoxDataModel(id=str(i.get('key')), name=i.get('title')) for i in response_model.data]

    def debug(self, row):
        user_info = UserModel()
        if user_info.selected_environment is None:
            error_message(self, '请先在右上角选择测试环境后再开始测试！')
            return
        response_message(self, HTTP.ui.page_steps.ui_steps_run(user_info.selected_environment, row.get("id")))
