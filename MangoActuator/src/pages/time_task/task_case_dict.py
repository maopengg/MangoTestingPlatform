# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-10-16 17:35
# @Author : 毛鹏
from mango_ui import THEME

from src.tools.methods import Methods

table_column = [
    {'key': 'id', 'name': 'ID', 'width': 100},
    {'key': 'case', 'name': '用例名称', },
    {'key': 'ope', 'name': '操作', 'width': 100}
]
right_data = [
    {'name': '新增', 'theme': THEME.blue, 'action': 'add'},
    {'name': '返回', 'theme': THEME.orange, 'action': 'back'}
]
table_menu = [
    {'name': '删除', 'action': 'delete'}
]
field_list = [
    {'key': 'id', 'name': '任务ID'},
    {'key': 'name', 'name': '任务名称'},
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
        'subordinate': 'case',

    },
    {
        'title': '用例名称',
        'placeholder': '请输入用例名称',
        'key': 'case',
        'type': 1,
    }
]
