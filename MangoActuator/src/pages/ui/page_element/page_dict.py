# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-05 11:56
# @Author : 毛鹏
from mango_ui import THEME
from src.settings import settings

search_data = [
    {
        'title': 'ID',
        'placeholder': '请输入页面ID',
        'key': 'id',
        'input': None
    },
    {
        'title': '页面名称',
        'placeholder': '请输入页面名称',
        'key': 'name',
        'input': None
    },
    {
        'title': '产品',
        'placeholder': '请选择项目产品',
        'key': 'project_product',
        'input': None
    },

    {
        'title': '模块',
        'placeholder': '请选择产品模块',
        'key': 'module',
        'input': None
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
        'select': lambda: settings.base_dict,
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
        'key': 'module',
        'name': '模块名称',
        'item': 'module',
        'width': 100
    },

    {
        'key': 'project_product',
        'name': '产品名称',
        'item': 'project_product',
        'width': 100
    },
    {
        'key': 'name',
        'name': '页面名称',
        'item': '',
        'width': 150
    },
    {
        'key': 'url',
        'name': 'URL',
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
        'action': 'subpage'
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
