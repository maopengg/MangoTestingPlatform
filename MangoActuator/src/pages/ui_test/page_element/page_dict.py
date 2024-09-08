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
        'select': None,
        'subordinate': 'module',
        'required': True
    },
    {
        'title': '模块',
        'placeholder': '请先选择项目/产品',
        'key': 'module',
        'type': 1,
        'select': None,
        'required': True
    },
    {
        'title': '页面名称',
        'placeholder': '请输入页面名称',
        'key': 'name',
        'type': 0,
        'required': True
    },

    {
        'title': '页面地址',
        'placeholder': '请输入页面地址',
        'key': 'url',
        'type': 0,
        'required': True
    },

]
table_column = [
    {
        'key': 'id',
        'name': 'ID',
        'item': ''
    },

    {
        'key': 'update_time',
        'name': '更新时间',
        'item': ''
    },

    {
        'key': 'module',
        'name': '模块名称',
        'item': 'module'
    },

    {
        'key': 'project_product',
        'name': '项目产品名称',
        'item': 'project_product'
    },

    {
        'key': 'create_Time',
        'name': '创建时间',
        'item': ''
    },
    {
        'key': 'name',
        'name': '页面名称',
        'item': ''
    },
    {
        'key': 'url',
        'name': 'URL',
        'item': ''
    },
    {
        'key': 'ope',
        'name': '操作',
        'item': ''
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
