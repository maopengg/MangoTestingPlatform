# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-09-05 11:56
# @Author : 毛鹏
title_data = [
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
        'title': '所属页面',
        'placeholder': '请选择步骤所属页面',
        'key': 'page',
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
        'name': '步骤名称',
        'item': '',
        'width': 150
    },
    {
        'key': 'run_flow',
        'name': '顺序',
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
        'name': '添加步骤',
        'action': 'add_step'
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
