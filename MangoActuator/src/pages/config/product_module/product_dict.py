# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-05 11:56
# @Author : 毛鹏
from mango_ui import THEME

from src.enums.system_enum import AutoTestTypeEnum
from src.enums.tools_enum import ProductTypeEnum
from src.tools.methods import Methods

search_data = [
    {
        'title': 'ID',
        'placeholder': '请输入ID',
        'key': 'id',
        'input': None
    },
    {
        'title': '页面名称',
        'placeholder': '请输入页面名称',
        'key': 'name',
        'input': None
    },
    {
        'title': '产品',
        'placeholder': '请选择项目产品',
        'key': 'project_product',
        'input': None
    },

    {
        'title': '模块',
        'placeholder': '请选择产品模块',
        'key': 'module',
        'input': None
    }
]
right_data = [
    {'name': '新增', 'theme': THEME.blue, 'action': 'add'}

]
form_data = [
    {
        'title': '项目',
        'placeholder': '请选择项目产品',
        'key': 'project',
        'type': 1,
        'select': Methods.get_project_model,
    },
    {
        'title': '自动化类型',
        'placeholder': '请选择自动化类型',
        'key': 'auto_type',
        'type': 1,
        'select': AutoTestTypeEnum.get_select()
    },
    {
        'title': '产品类型',
        'placeholder': '请选择产品类型',
        'key': 'client_type',
        'type': 1,
        'select': ProductTypeEnum.get_select()
    },
    {
        'title': '产品名称',
        'placeholder': '请输入产品名称',
        'key': 'name',
    },

]
table_column = [
    {
        'key': 'id',
        'name': 'ID',
        'width': 7
    },
    {
        'key': 'create_time',
        'name': '创建时间',
        'width': 120
    },

    {
        'key': 'update_time',
        'name': '更新时间',
        'width': 120
    },
    {
        'key': 'project',
        'name': '项目名称',
        'width': 80
    },
    {
        'key': 'name',
        'name': '产品名称',
    },
    {
        'key': 'auto_type',
        'name': '自动化类型',
        'width': 80,
        'option': AutoTestTypeEnum.get_option('value', 'label')
    },
    {
        'key': 'client_type',
        'name': '产品类型',
        'width': 200,
        'option': ProductTypeEnum.get_option('value', 'label')
    },
    {
        'key': 'ope',
        'name': '操作',
        'width': 120
    },

]
table_menu = [
    {
        'name': '编辑',
        'action': 'edit'
    },
    {
        'name': '添加模块',
        'action': 'subpage'
    },
    {
        'name': '删除',
        'action': 'delete'
    }

]
