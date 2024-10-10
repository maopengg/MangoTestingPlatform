# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-08 9:56
# @Author : 毛鹏
import threading

from mango_ui import *

from src.models.tools_model import BaseDictModel
from src.network import Http
from src.tools.other.get_class_methods import GetClassMethod


class Methods:
    base_dict: BaseDictModel = BaseDictModel(ui_option=GetClassMethod().option())

    @classmethod
    def set_product_module(cls, parent, data: DialogCallbackModel) -> list[ComboBoxDataModel]:
        for e in cls.base_dict.project:
            for q in e.children:
                if q.value == data.value:
                    init_data = []
                    for i in q.children:
                        init_data.append(ComboBoxDataModel(id=i.value, name=i.label))
                    if init_data == {}:
                        error_message(parent, '您选择的项目还没创建模块，请先创建模块！')
                    return init_data

    @classmethod
    def get_product_module_label(cls, product_id: int):
        for e in cls.base_dict.project:
            for q in e.children:
                if q.value == product_id:
                    return q.children

    @classmethod
    def set_project(cls):
        def run():
            cls.base_dict.project = [CascaderModel(**i) for i in Http.project_info()['data']]
        thread = threading.Thread(target=run)
        thread.start()
