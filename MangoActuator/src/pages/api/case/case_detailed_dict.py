# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-05 11:56
# @Author : 毛鹏
from mango_ui import THEME

from src.enums.tools_enum import TaskEnum
from src.tools.methods import Methods

table_column = [
    {'key': 'api_info', 'name': '接口名称'},
    # {'key': 'method', 'name': '请求方法', 'width': 70, 'option': MethodEnum.get_option('value', 'label')},
    {'key': 'status', 'name': '测试结果', 'width': 100, 'option': TaskEnum.get_option('value', 'label')},
    {'key': 'ope', 'name': '操作', 'type': 1, 'width': 120},
]
right_data = [
    {'name': '新增', 'theme': THEME.group.info, 'action': 'add'},
    {'name': '执行', 'theme': THEME.group.success, 'action': 'run'},
    {'name': '返回', 'theme': THEME.group.warning, 'action': 'back'}
]
table_menu = [
    {'name': '刷新', 'action': 'refresh'},
    {'name': '删除', 'action': 'delete'}
]
field_list = [
    {'key': 'id', 'name': 'ID'},
    {'key': 'name', 'name': '用例名称'},
    {'key': 'case_people', 'name': '负责人'},
    {'key': 'case_flow', 'name': '执行顺序'},
]
form_data = [
    {
        'title': '产品/模块',
        'placeholder': '请选择产品/模块',
        'key': 'module',
        'type': 2,
        'select': Methods.get_product_module_label_model,
        'subordinate': 'api_info'
    },
    {
        'title': '接口名称',
        'placeholder': '请选择接口',
        'key': 'api_info',
        'type': 1,
    },
]
