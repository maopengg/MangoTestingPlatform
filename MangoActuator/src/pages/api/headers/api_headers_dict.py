# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-05 11:56
# @Author : 毛鹏
from mangoui import THEME

from src.enums.tools_enum import Status5Enum
from src.tools.methods import Methods

search_data = [
    {
        'title': 'ID',
        'placeholder': '请输入ID',
        'key': 'id',
    },
]
right_data = [
    {'name': '新增', 'theme': THEME.group.info, 'action': 'add'}

]
form_data = [
    {
        'title': '项目/产品',
        'placeholder': '请选择项目产品',
        'key': 'project_product',
        'type': 2,
        'select': Methods.get_product_module_cascader_model,
    },

    {
        'title': 'key',
        'placeholder': '请输入引用key',
        'key': 'key',
    },
    {
        'title': 'value',
        'placeholder': '请输入value值',
        'key': 'value',
    },
    {
        'title': '默认使用',
        'placeholder': '是否默认使用',
        'key': 'status',
        'type': 3
    },

]
table_column = [
    {
        'key': 'id',
        'name': 'ID',
        'width': 7
    },
    {
        'key': 'project_product',
        'name': '产品名称',
        'width': 100
    },
    {
        'key': 'key',
        'name': 'key',
        'width': 150,

    },
    {
        'key': 'value',
        'name': 'value',
    },
    {
        'key': 'status',
        'name': '默认使用',
        'width': 100,
        'option': Status5Enum.get_option('value', 'label')
    },
    {
        'key': 'ope',
        'name': '操作',
        'type': 1,
        'width': 120
    },

]
table_menu = [
    {
        'name': '编辑',
        'action': 'edit'
    },
    {
        'name': '删除',
        'action': 'delete'
    }
]
