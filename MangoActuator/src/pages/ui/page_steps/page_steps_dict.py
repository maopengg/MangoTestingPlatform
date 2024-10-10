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
        'placeholder': '请输入步骤ID',
        'key': 'id',
    },
    {
        'title': '步骤名称',
        'placeholder': '请输入步骤名称',
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
    },
    {
        'title': '所属页面',
        'placeholder': '请选择所属页面',
        'key': 'page',
    },
    {
        'title': '状态',
        'placeholder': '请选择步骤状态',
        'key': 'status',
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
        'subordinate': 'page',
    },
    {
        'title': '所属页面',
        'placeholder': '请选择步骤所属页面',
        'key': 'page',
        'type': 1,
    },
    {
        'title': '步骤名称',
        'placeholder': '步骤名称',
        'key': 'name',
    },

]
table_column = [
    {
        'key': 'id',
        'name': 'ID',
        'width': 7
    },
    {
        'key': 'module',
        'name': '模块名称',
        'width': 100
    },
    {
        'key': 'project_product',
        'name': '产品名称',
        'width': 100
    },
    {
        'key': 'name',
        'name': '步骤名称',
        'width': 150
    },
    {
        'key': 'run_flow',
        'name': '顺序',
    },
    {
        'key': 'ope',
        'name': '操作',
        'width': 120
    },

]
table_menu = [
    {
        'name': '调试',
        'action': 'debug'
    },
    {
        'name': '详情',
        'action': 'subpage'
    },
    {
        'name': '···',
        'action': '',
        'son': [
            {
                'name': '编辑',
                'action': 'edit'
            },
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
