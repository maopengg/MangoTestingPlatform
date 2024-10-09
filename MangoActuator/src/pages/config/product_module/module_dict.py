# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-05 11:56
# @Author : 毛鹏
from mango_ui import THEME


table_column = [
    {'key': 'id', 'name': '序号', 'width': 40},
    {'key': 'create_time', 'name': '创建时间', 'width': 150},
    {'key': 'update_time', 'name': '更新时间', 'width': 150},
    {'key': 'name', 'name': '模块名称',},
    {'key': 'superior_module', 'name': '上级模块(一级模块)', 'width': 150 },
    {'key': 'ope', 'name': '操作', 'width': 120},
]
right_data = [
    {'name': '新增', 'theme': THEME.blue, 'action': 'add'},
    {'name': '返回', 'theme': THEME.orange, 'action': 'back'}
]
table_menu = [
    {'name': '编辑', 'action': 'edit'},
    {'name': '删除', 'action': 'delete'}
]
field_list = [
    {'key': 'id', 'name': '产品ID'},
    {'key': 'name', 'name': '产品名称'},
]
form_data = [
    {
        'title': '模块名称',
        'placeholder': '请输入模块名称',
        'key': 'name',
    },
    {
        'title': '上级模块',
        'placeholder': '请输入上级模块名称',
        'key': 'superior_module',
        'required': False,
    }
]
