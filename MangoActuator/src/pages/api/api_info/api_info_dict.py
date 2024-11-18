# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-05 11:56
# @Author : 毛鹏
from mango_ui import THEME

from src.enums.api_enum import MethodEnum
from src.enums.tools_enum import Status3Enum
from src.tools.methods import Methods

search_data = [
    {
        'title': 'ID',
        'placeholder': '请输入ID',
        'key': 'id',
    },
    {
        'title': '名称',
        'placeholder': '请输入名称',
        'key': 'name',
    },
    {
        'title': '项目/产品',
        'placeholder': '请选择项目产品',
        'key': 'project_product',
        'type': 2,
        'select': Methods.get_product_module_cascader_model,
        'subordinate': 'module'
    },

    {
        'title': '模块',
        'placeholder': '请选择模块',
        'key': 'module',
        'type': 1,
    }
]
right_data = [
    {'name': '新增', 'theme': THEME.group.info, 'action': 'add'},
    {'name': '导入', 'theme': THEME.group.info, 'action': 'import'}

]
form_data = [
    {
        'title': '项目/产品',
        'placeholder': '请选择项目产品',
        'key': 'project_product',
        'type': 2,
        'subordinate': 'module',
        'select': Methods.get_product_module_cascader_model,
    },
    {
        'title': '模块',
        'placeholder': '请先选择项目/产品',
        'key': 'module',
        'type': 1,
    },
    {
        'title': '接口名称',
        'placeholder': '请输入接口名称',
        'key': 'name',
    },

    {
        'title': 'URL路径',
        'placeholder': '请输入URL后的路径',
        'key': 'url',
    },
    {
        'title': '请求方法',
        'placeholder': '请选择请求方法',
        'key': 'method',
        'type': 1,
        'select': MethodEnum.get_select()
    },

]
table_column = [
    {
        'key': 'id',
        'name': 'ID',
        'width': 7
    },
    {
        'key': 'project_product',
        'name': '产品名称',
        'width': 100
    },
    {
        'key': 'module',
        'name': '模块名称',
        'width': 100
    },
    {
        'key': 'name',
        'name': '接口名称',
        'width': 150
    },
    {
        'key': 'url',
        'name': 'URL',
    },
    {
        'key': 'method',
        'name': '方法',
        'width': 100,
        'option': MethodEnum.get_option('value', 'label')

    },
    {
        'key': 'status',
        'name': '状态',
        'width': 100,
        'option': Status3Enum.get_option('value', 'label')
    },
    {
        'key': 'ope',
        'name': '操作',
        'width': 120
    },

]
table_menu = [
    {
        'name': '执行',
        'action': 'run'
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
