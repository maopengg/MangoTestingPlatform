# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-05 11:56
# @Author : 毛鹏
from mango_ui import THEME
from src.enums.tools_enum import Status1Enum
from src.enums.ui_enum import ElementExpEnum

table_column = [
    {'key': 'name', 'name': '元素名称', 'width': 100},
    {'key': 'exp', 'name': '表达式类型', 'width': 70, 'option': ElementExpEnum.get_option('value', 'label')},
    {'key': 'loc', 'name': '定位表达式',  },
    {'key': 'is_iframe', 'name': '是否在iframe中', 'width': 40, 'option': Status1Enum.get_option('value', 'label')},
    {'key': 'sleep', 'name': '等待时间（秒）', 'width': 40},
    {'key': 'sub', 'name': '元素下标（1开始）', 'width': 40},
    {'key': 'ope', 'name': '操作', 'width': 120},
]
right_data = [
    {'name': '新增', 'theme': THEME.blue, 'action': 'add'},
    {'name': '返回', 'theme': THEME.orange, 'action': 'back'}
]
table_menu = [
    {'name': '调试', 'action': 'debug'},
    {'name': '编辑', 'action': 'edit'},
    {'name': '删除', 'action': 'delete'}
]
field_list = [
    {'key': 'id', 'name': '页面ID'},
    {'key': 'url', 'name': '页面地址'},
    {'key': 'name', 'name': '页面名称'},
]
form_data = [
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
