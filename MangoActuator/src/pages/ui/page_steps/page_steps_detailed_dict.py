# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-05 11:56
# @Author : 毛鹏
from mango_ui import THEME

from src.enums.ui_enum import ElementOperationEnum
from src.network import HTTP
from src.tools.methods import Methods

right_data = [
    {'name': '新增', 'theme': THEME.group.info, 'action': 'add'},
    {'name': '调试', 'theme': THEME.group.success, 'action': 'debug'},
    {'name': '返回', 'theme': THEME.group.warning, 'action': 'back'}
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
        'title': '元素名称',
        'placeholder': '请输入元素名称',
        'key': 'ele_name',
        'type': 1,
        'required': False,
        'select': HTTP.get_element_name
    },
    {
        'title': '操作值',
        'placeholder': '请输入元素操作值',
        'key': 'ope_value',
        'type': 5,
    },
]
table_column = [
    {'key': 'type', 'name': '操作类型', 'width': 70, 'option': ElementOperationEnum.get_option('value', 'label')},
    {'key': 'ele_name', 'name': '元素名称', 'width': 120},
    {'key': 'ope_key', 'name': '操作名称', 'width': 120, 'option': Methods.base_dict.ui_option},
    {'key': 'ope_value', 'name': '操作输入', },
    {'key': 'ope', 'name': '操作', 'width': 120},

]
table_menu = [
    {'name': ' ↑ ', 'action': 'move_up'},
    {'name': ' ↓ ', 'action': 'move_down'},
    {'name': '编辑', 'action': 'edit'},
    {'name': '删除', 'action': 'delete'}
]
