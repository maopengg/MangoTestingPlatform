# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-01 下午9:01
# @Author : 毛鹏
import json
from copy import deepcopy

from mango_ui import DialogCallbackModel, DialogWidget, FormDataModel, error_message

from src.enums.ui_enum import ElementOperationEnum
from src.models.user_model import UserModel
from src.network import HTTP
from src.pages.parent.sub import SubPage
from src.tools.components.message import response_message
from src.tools.get_class_methods import GetClassMethod
from .element_dict import *


class ElementPage(SubPage):
    debug_form_data = [
        {
            'title': '步骤类型',
            'placeholder': '请选择元素表达式类型',
            'key': 'type',
            'type': 1,
            'select': ElementOperationEnum.get_select(),
            'subordinate': 'ope_key'
        },

        {
            'title': '步骤操作',
            'placeholder': '元素表达式',
            'key': 'ope_key',
            'type': 2,
            'subordinate': 'ope_value'
        },
        {
            'title': '操作值',
            'placeholder': '请输入元素操作值',
            'key': 'ope_value',
            'type': 5,
        }
    ]

    def __init__(self, parent):
        super().__init__(parent,
                         table_column=table_column,
                         right_data=right_data,
                         table_menu=table_menu,
                         field_list=field_list,
                         form_data=form_data)
        self.superior_page = 'page'
        self.id_key = 'page'
        self.get = HTTP.ui.element.get_page_element
        self.post = HTTP.ui.element.post_page_element
        self.put = HTTP.ui.element.put_page_element
        self._delete = HTTP.ui.element.delete_page_element
        self.select_data = None

    def sub_options(self, data: DialogCallbackModel, is_refresh=True):
        client_type = self.data.get('project_product').get('client_type')
        if data.subordinate == 'ope_key':
            self.select_data = GetClassMethod.ope_select_data(int(data.value), client_type)
            if data.subordinate_input_object:
                data.subordinate_input_object.set_select(self.select_data, True)
            return self.select_data
        elif data.subordinate == 'ope_value':
            ope_value: dict = GetClassMethod.find_parameter_by_value(self.select_data, data.value)
            if ope_value == {'locating': ''} or ope_value == {}:
                data.subordinate_input_object.setReadOnly(True)
            else:
                data.subordinate_input_object.setReadOnly(False)
            if data.subordinate_input_object:
                data.subordinate_input_object.set_value(json.dumps(ope_value))

    def debug(self, row):
        user_info = UserModel()
        if user_info.selected_environment is None:
            error_message(self, '请先在右上角选择测试环境后再开始测试！')
            return
        form_data = [FormDataModel(**i) for i in deepcopy(self.debug_form_data)]
        if hasattr(self, 'dialog_widget_size'):
            dialog = DialogWidget('调试元素', form_data, self.dialog_widget_size)
        else:
            dialog = DialogWidget('调试元素', form_data)
        dialog.clicked.connect(self.sub_options)
        dialog.exec()
        if dialog.data:
            response_model = HTTP.ui.element.test_element(
                test_env=user_info.selected_environment,
                page_id=row['page']['id'],
                element_id=row['id'],
                project_product_id=row['page']['project_product'],
                _type=dialog.data['type'],
                ope_key=dialog.data['ope_key'],
                ope_value=json.loads(dialog.data['ope_value']),
            )
            if response_model:
                response_message(self, response_model)
            self.show_data()
