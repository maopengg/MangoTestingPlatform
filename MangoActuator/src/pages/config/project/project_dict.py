# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-05 11:56
# @Author : 毛鹏
from mangoui import THEME

from src.enums.tools_enum import Status5Enum

search_data = [
    {
        'title': 'ID',
        'placeholder': '请输入ID',
        'key': 'id',
    },
    {
        'title': '项目名称',
        'placeholder': '请输入项目名称',
        'key': 'name',
    },
]
right_data = [
    {'name': '新增', 'theme': THEME.group.info, 'action': 'add'}
]
form_data = [
    {
        'title': '项目名称',
        'placeholder': '请输入项目名称',
        'key': 'name',
    },
    {
        'title': '状态',
        'placeholder': '请选择项目的启用状态',
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
        'key': 'create_time',
        'name': '创建时间',
        'width': 100
    },

    {
        'key': 'update_time',
        'name': '更新时间',
        'width': 100
    },
    {
        'key': 'name',
        'name': '项目名称',
        'width': 150
    },
    {
        'key': 'status',
        'name': '状态',
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
