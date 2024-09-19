# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-01 下午9:01
# @Author : 毛鹏
from src.enums.ui_enum import ElementExpEnum

table_column = [
    {'key': 'name', 'name': '元素名称', 'item': '', 'width': 100},
    {'key': 'exp', 'name': '表达式类型', 'item': '', 'width': 70},
    {'key': 'loc', 'name': '定位表达式', 'item': '', },
    {'key': 'is_iframe', 'name': '是否在iframe中', 'item': '', 'width': 40},
    {'key': 'sleep', 'name': '等待时间（秒）', 'item': '', 'width': 40},
    {'key': 'sub', 'name': '元素下标（1开始）', 'item': '', 'width': 40},
    {'key': 'ope', 'name': '操作', 'item': '', 'width': 120},
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
