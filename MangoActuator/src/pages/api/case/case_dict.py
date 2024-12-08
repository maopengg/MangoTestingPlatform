# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-05 11:56
# @Author : 毛鹏
from mango_ui import THEME

from src.enums.tools_enum import TaskEnum, CaseLevelEnum
from src.network import HTTP
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
        'title': '产品',
        'placeholder': '请选择项目产品',
        'key': 'project_product',
        'type': 2,
        'select': Methods.get_product_module_cascader_model,
        'subordinate': 'module'
    },
    {
        'title': '模块',
        'placeholder': '请选择产品模块',
        'key': 'module',
        'type': 1,
    },
    {
        'title': '状态',
        'placeholder': '请选择步骤状态',
        'key': 'status',
        'type': 1,
        'select': TaskEnum.get_select()
    }
]
right_data = [
    {'name': '新增', 'theme': THEME.group.info, 'action': 'add'},
    {'name': '批量执行', 'theme': THEME.group.success, 'action': 'batch_run'},

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
        'title': '用例名称',
        'placeholder': '请输入用例名称',
        'key': 'name',
    },
    {
        'title': '用例级别',
        'placeholder': '请设置用例级别',
        'key': 'level',
        'type': 1,
        'select': CaseLevelEnum.get_select()
    },
    {
        'title': '用例负责人',
        'placeholder': '请设置用例负责人',
        'key': 'case_people',
        'type': 1,
        'select': HTTP.get_name
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
        'name': '用例名称',
        'width': 150
    },
    {
        'key': 'case_flow',
        'name': '用例顺序',
    },
    {
        'key': 'level',
        'name': '用例级别',
        'width': 100,
        'option': CaseLevelEnum.get_option('value', 'label')
    },
    {
        'key': 'case_people',
        'name': '用例负责人',
        'width': 100,
    },
    {
        'key': 'status',
        'name': '状态',
        'width': 100,
        'option': TaskEnum.get_option('value', 'label')

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
        'name': '步骤',
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
