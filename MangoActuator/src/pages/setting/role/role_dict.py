# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-05 11:56
# @Author : 毛鹏
from mango_ui import THEME

right_data = [
    {'name': '新增', 'theme': THEME.group.info, 'action': 'add'}

]
form_data = [
    {
        'title': '角色名称',
        'placeholder': '请输入角色名称',
        'key': 'name',
    },
    {
        'title': '角色描述',
        'placeholder': '请输入角色描述',
        'key': 'description',
    },
]
table_column = [
    {
        'key': 'id',
        'name': 'ID',
        'width': 7
    },
    {
        'key': 'name',
        'name': '角色名称',
        'width': 300
    },

    {
        'key': 'description',
        'name': '角色描述',
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
