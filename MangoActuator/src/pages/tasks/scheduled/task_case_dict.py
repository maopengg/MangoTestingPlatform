# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-10-16 17:35
# @Author : 毛鹏
from mango_ui import THEME

from src.tools.methods import Methods

table_column = [
    {'key': 'id', 'name': 'ID', 'width': 100},
    {'key': 'case_id', 'name': '用例名称', },
    {'key': 'ope', 'name': '操作', 'width': 100}
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
        'placeholder': '请选择产品模块后选择用例',
        'key': 'module',
        'type': 2,
        'subordinate': 'case_id',
        'select': Methods.product_module,
    },
    {
        'title': '用例名称',
        'placeholder': '请输入用例名称',
        'key': 'case_id',
        'type': 1,
    }
]
