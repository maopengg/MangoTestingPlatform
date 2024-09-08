# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2024-09-08 9:56
# @Author : 毛鹏
from src.components import error_message
from src.models.gui_model import DialogCallbackModel, ComboBoxDataModel
from src.settings import settings


def set_product_module(parent, data: DialogCallbackModel) -> list[ComboBoxDataModel]:
    for e in settings.base_dict:
        for q in e.children:
            if q.value == data.value:
                init_data = []
                for i in q.children:
                    init_data.append(ComboBoxDataModel(id=i.value, name=i.label))
                if init_data == {}:
                    error_message(parent, '您选择的项目还没创建模块，请先创建模块！')
                return init_data


def get_product_module_label(product_id: int):
    for e in settings.base_dict:
        for q in e.children:
            if q.value == product_id:
                return q.children
