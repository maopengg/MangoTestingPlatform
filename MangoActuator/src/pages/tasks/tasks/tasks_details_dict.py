# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-10-16 17:35
# @Author : 毛鹏
from mangoui import THEME

from src.tools.methods import Methods

table_column = [
    {'key': 'id', 'name': 'ID', 'width': 100},
    {'key': 'case_id', 'name': '用例名称', },
    {'key': 'command', 'name': '命令', },
    {'key': 'ope', 'name': '操作', 'type': 1, 'width': 100}
]
right_data = [
    {'name': '新增', 'theme': THEME.group.info, 'action': 'add'},
    {'name': '返回', 'theme': THEME.group.warning, 'action': 'back'}
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
        'title': '模块',
        'placeholder': '请选择模块',
        'key': 'module',
        'type': 1,
        'subordinate': 'case_id',
        'select': Methods.get_product_module_label,
    },
    {
        'title': '用例名称',
        'placeholder': '请输入用例名称',
        'key': 'case_id',
        'type': 1,
    }
]
cmd_form_data = [
    {
        'title': 'cmd命令',
        'placeholder': '请输入单个的cmd命令',
        'key': 'command',
    }
]
