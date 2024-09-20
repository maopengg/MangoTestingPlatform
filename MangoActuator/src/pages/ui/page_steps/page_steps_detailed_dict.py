# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-05 11:56
# @Author : 毛鹏
from src import THEME, UI_OPE_METHOD
from src.enums.ui_enum import ElementExpEnum, ElementOperationEnum
table_column = [
    {'key': 'type', 'name': '操作类型', 'width': 100, 'option': ElementOperationEnum.get_option('value', 'label')},
    {'key': 'ele_name', 'name': '元素名称', 'width': 70},
    {'key': 'ope_key', 'name': '操作名称', 'width': 100, 'option': UI_OPE_METHOD},
    {'key': 'ope_value', 'name': '操作输入', },
    {'key': 'ope', 'name': '操作', 'width': 120},

]
table_menu = [
    {'name': '编辑', 'action': 'edit'},
    {'name': '删除', 'action': 'delete'}
]
right_data = [
    {'name': '新增', 'theme': THEME.blue, 'action': 'add'},
    {'name': '调试', 'theme': THEME.green, 'action': 'debug'},
    {'name': '返回', 'theme': THEME.orange, 'action': 'back'}
]
field_list = [
    {'key': 'id', 'name': '步骤ID'},
    {'key': 'name', 'name': '步骤名称'},
    {'key': 'type', 'name': '调试状态'},
    {'key': 'run_flow', 'name': '步骤顺序'},
]
form_data = [
    {
        'title': '步骤类型',
        'placeholder': '请选择元素表达式类型',
        'key': 'exp',
        'type': 1,
        'select': ElementOperationEnum.get_select(),
        'subordinate': 'ope_key'
    },
    {
        'title': '步骤操作',
        'placeholder': '元素表达式',
        'key': 'ope_key',
        'type': 2,
    },
    {
        'title': '元素名称',
        'placeholder': '请输入元素名称',
        'key': 'name',
        'type': 0,
        'required': False
    },
    {
        'title': '操作值',
        'placeholder': '请输入元素操作值',
        'key': 'ope_value',
    },

]
