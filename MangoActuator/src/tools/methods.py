# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-08 9:56
# @Author : 毛鹏
import threading

from mangoui import *

from src.models.tools_model import BaseDictModel
from src.network import HTTP


# from src.tools.get_class_methods import GetClassMethod


class Methods:
    base_dict: BaseDictModel = None

    # base_dict: BaseDictModel = BaseDictModel(ui_option=GetClassMethod().option())

    @classmethod
    def get_product_module(cls, parent, data: DialogCallbackModel) -> list[ComboBoxDataModel]:
        """"""
        for e in cls.base_dict.project:
            for q in e.children:
                if q.value == str(data.value):
                    init_data = []
                    for i in q.children:
                        init_data.append(ComboBoxDataModel(id=i.value, name=i.label))
                    if init_data == {}:
                        error_message(parent, '您选择的项目还没创建模块，请先创建模块！')
                    return init_data

    @classmethod
    def get_product_module_label(cls, product_id: str) -> list[ComboBoxDataModel]:
        for e in cls.base_dict.project:
            for q in e.children:
                if q.value == str(product_id):
                    return [ComboBoxDataModel(id=str(children.value), name=children.label) for children in q.children]

    @classmethod
    def get_product_module_cascader_model(cls) -> list[CascaderModel]:
        return cls.base_dict.project

    @classmethod
    def product_module(cls, project_id: int) -> list[CascaderModel]:
        for i in cls.base_dict.project:
            if i.value == str(project_id):
                return i.children

    @classmethod
    def get_project_model(cls) -> list[ComboBoxDataModel]:
        return [ComboBoxDataModel(id=str(i.value) if i.value else None, name=i.label) for i in cls.base_dict.project]

    @classmethod
    def set_project(cls):
        def run():
            cls.base_dict.project = [cls.convert_to_cascader_model(i) for i in
                                     HTTP.system.project.project_product_name('1').data]

        thread = threading.Thread(target=run)
        thread.start()

    @classmethod
    def convert_to_cascader_model(cls, data):
        return CascaderModel(
            value=str(data['value']),
            label=data['label'],
            parameter=data.get('parameter'),
            children=[cls.convert_to_cascader_model(child) for child in data.get('children', [])]
        )

    @classmethod
    def get_product_module_label_model(cls, product_id):
        for i in cls.base_dict.project:
            if i.children:
                for e in i.children:
                    if e.value == str(product_id):
                        return i.children
