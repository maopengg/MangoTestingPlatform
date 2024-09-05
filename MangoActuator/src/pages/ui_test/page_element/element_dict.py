# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-09-05 11:56
# @Author : 毛鹏
table_column = [
    {'key': 'name', 'name': '元素名称', 'item': ''},
    {'key': 'exp', 'name': '表达式类型', 'item': ''},
    {'key': 'loc', 'name': '定位表达式', 'item': ''},
    {'key': 'is_iframe', 'name': '是否在iframe中', 'item': ''},
    {'key': 'sleep', 'name': '等待时间（秒）', 'item': ''},
    {'key': 'sub', 'name': '元素下标（1开始）', 'item': ''},
    {'key': 'ope', 'name': '操作', 'item': ''},
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
from_data = [
    {
        'title': '元素名称',
        'placeholder': '请输入元素名称',
        'key': 'name',
        'input': None,
        'text': None,
        'type': 0
    },
    {
        'title': '表达式类型',
        'placeholder': '请选择元素表达式类型',
        'key': 'exp',
        'input': None,
        'text': None,
        'type': 0
    },
    {
        'title': '元素表达式',
        'placeholder': '元素表达式',
        'key': 'loc',
        'input': None,
        'text': None,
        'type': 0
    },
    {
        'title': '等待时间',
        'placeholder': '请输入元素等待时间',
        'key': 'sleep',
        'input': None,
        'text': None,
        'type': 0
    },
    {
        'title': '元素下标',
        'placeholder': '请输入元素下标',
        'key': 'sub',
        'input': None,
        'text': None,
        'type': 0
    }
]
