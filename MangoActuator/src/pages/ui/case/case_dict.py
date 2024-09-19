# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-08-28 16:30
# @Author : 毛鹏
from src import THEME

search_data = [
    {
        'title': 'ID',
        'placeholder': '请输入页面ID',
        'key': 'id',
    },
    {
        'title': '页面名称',
        'placeholder': '请输入页面名称',
        'key': 'name',
    },
    {
        'title': '产品',
        'placeholder': '请选择项目产品',
        'key': 'project_product',
    },

    {
        'title': '模块',
        'placeholder': '请选择产品模块',
        'key': 'module',
    }
]
right_data = [
    {'name': '新增', 'theme': THEME.blue, 'action': 'add'}

]
form_data = [
    {
        'title': '项目/产品',
        'placeholder': '请选择项目产品',
        'key': 'project_product',
        'type': 2,
        'subordinate': 'module',
    },
    {
        'title': '模块',
        'placeholder': '请先选择项目/产品',
        'key': 'module',
        'type': 1,
    },
    {
        'title': '页面名称',
        'placeholder': '请输入页面名称',
        'key': 'name',
    },

    {
        'title': '页面地址',
        'placeholder': '请输入页面地址',
        'key': 'url',
    },

]
table_column = [
    {
        'key': 'id',
        'name': 'ID',
        'item': '',
        'width': 7
    },
    {
        'key': 'project_product',
        'name': '项目/产品',
        'item': 'name',
        'width': 100
    },

    {
        'key': 'module',
        'name': '模块',
        'item': 'name',
        'width': 100
    },
    {
        'key': 'name',
        'name': '用例名称',
        'item': '',
        'width': 100
    },
    {
        'key': 'case_flow',
        'name': '步骤顺序',
        'item': ''
    },
    {
        'key': 'ope',
        'name': '操作',
        'item': '',
        'width': 120
    },

]
table_menu = [
    {
        'name': '编辑',
        'action': 'edit'
    },
    {
        'name': '添加元素',
        'action': 'add_ele'
    },
    {
        'name': '···',
        'action': '',
        'son': [
            {
                'name': '复制',
                'action': 'copy'
            },
            {
                'name': '删除',
                'action': 'delete'
            }
        ]
    }
]
