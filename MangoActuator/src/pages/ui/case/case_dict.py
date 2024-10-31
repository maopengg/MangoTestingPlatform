# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-28 16:30
# @Author : 毛鹏
from mango_ui import THEME

from src.enums.system_enum import CaseLevelEnum
from src.enums.tools_enum import Status3Enum
from src.network import HTTP
from src.tools.methods import Methods

search_data = [
    {
        'title': 'ID',
        'placeholder': '请输入页面ID',
        'key': 'id',
    },
    {
        'title': '用例名称',
        'placeholder': '请输入用例名称',
        'key': 'name',
    },

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
        'select': HTTP.get_nickname
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
        'name': '项目/产品',
        'item': 'name',
        'width': 100
    },

    {
        'key': 'module',
        'name': '模块',
        'width': 100
    },
    {
        'key': 'name',
        'name': '用例名称',
        'width': 100
    },
    {
        'key': 'case_flow',
        'name': '步骤顺序',
    },
    {
        'key': 'level',
        'name': '级别',
        'width': 100,
        'option': CaseLevelEnum.get_option('value', 'label')
    },
    {
        'key': 'case_people',
        'name': '负责人',
        'width': 100
    },
    {
        'key': 'status',
        'name': '结果',
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
