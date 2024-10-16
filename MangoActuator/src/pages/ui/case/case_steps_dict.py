# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-01 下午9:01
# @Author : 毛鹏
from mango_ui import THEME

from src.enums.tools_enum import Status3Enum
from src.enums.ui_enum import ElementOperationEnum
from src.network import Http
from src.tools.methods import Methods

table_column = [
    {'key': 'page_step', 'name': '步骤名称', 'width': 150, },
    {'key': 'status', 'name': '测试结果', 'width': 70, 'option': Status3Enum.get_option('value', 'label')},
    {'key': 'error_message', 'name': '错误提示', },
    {'key': 'ope', 'name': '操作', 'width': 70},

]
table_menu = [
    {'name': '同步', 'action': 'refresh_case'},
    {'name': '删除', 'action': 'delete'}
]
right_data = [
    {'name': '新增', 'theme': THEME.blue, 'action': 'add'},
    # {'name': '刷新步骤', 'theme': THEME.blue, 'action': 'refresh_case'},
    {'name': '执行', 'theme': THEME.green, 'action': 'run'},
    {'name': '返回', 'theme': THEME.orange, 'action': 'back'}
]
field_list = [
    {'key': 'id', 'name': '用例ID'},
    {'key': 'name', 'name': '用例名称'},
    {'key': 'status', 'name': '用例状态'},
    {'key': 'case_flow', 'name': '步骤顺序'},
]
form_data = [
    {
        'title': '产品/模块',
        'placeholder': '请选择产品/模块',
        'key': 'module',
        'type': 2,
        'select': Methods.get_product_module_label_model,
        'subordinate': 'page'
    },
    {
        'title': '选择页面',
        'placeholder': '请选择测试页面',
        'key': 'page',
        'type': 1,
        'subordinate': 'page_step'
    },
    {
        'title': '页面步骤',
        'placeholder': '请选择页面步骤',
        'key': 'page_step',
        'type': 1,
        'required': False,
    },


]
