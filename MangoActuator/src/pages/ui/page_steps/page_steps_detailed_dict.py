# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-05 11:56
# @Author : 毛鹏
from src import THEME
from src.enums.ui_enum import ElementExpEnum

table_column = [
    {'key': 'type', 'name': '操作类型', 'width': 100},
    {'key': 'ele_name', 'name': '元素名称', 'width': 70},
    {'key': 'ope_type', 'name': '元素操作类型',  'width': 70},
    {'key': 'ope_value', 'name': '元素操作值', },
    {'key': 'ass_type', 'name': '断言类型', 'width': 70},
    {'key': 'ass_value', 'name': '断言操作值', 'width': 70},
    {'key': 'key_list', 'name': 'key_list', 'width': 70},
    {'key': 'sql', 'name': 'sql', 'width': 40},
    {'key': 'key', 'name': 'key', 'width': 40},
    {'key': 'value', 'name': 'value', 'width': 40},
    {'key': 'ope', 'name': '操作', 'width': 120},

]
right_data = [
    {'name': '新增', 'theme': THEME.blue, 'action': 'add'},
    {'name': '调试', 'theme': THEME.blue, 'action': 'debug'},
    {'name': '返回', 'theme': THEME.orange, 'action': 'back'}
]
table_menu = [
    {'name': '编辑', 'action': 'edit'},
    {'name': '删除', 'action': 'delete'}
]

from_data = [
    {
        'title': '元素名称',
        'placeholder': '请输入元素名称',
        'key': 'name',
    },
    {
        'title': '表达式类型',
        'placeholder': '请选择元素表达式类型',
        'key': 'exp',
        'type': 1,
        'select': ElementExpEnum.get_select()
    },
    {
        'title': '元素表达式',
        'placeholder': '元素表达式',
        'key': 'loc',
    },
    {
        'title': '是否iframe',
        'placeholder': '元素是否在iframe中',
        'key': 'is_iframe',
        'type': 3,

    },
    {
        'title': '等待时间',
        'placeholder': '请输入元素等待时间',
        'key': 'sleep',
        'required': False
    },
    {
        'title': '元素下标',
        'placeholder': '请输入元素下标',
        'key': 'sub',
        'required': False
    }
]
