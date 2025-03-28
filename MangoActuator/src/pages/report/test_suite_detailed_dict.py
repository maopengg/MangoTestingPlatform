# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-05 11:56
# @Author : 毛鹏
from mangoui import THEME

right_data = [
    {'name': '刷新', 'theme': THEME.group.info, 'action': 'show_data'},
    {'name': '返回', 'theme': THEME.group.warning, 'action': 'back'}
]
field_list = [
    {'key': 'id', 'name': '测试套ID'},
    {'key': 'project_product', 'name': '项目名称'},
    {'key': 'create_time', 'name': '执行时间'},
    {'key': 'status', 'name': '测试结果'},
    {'key': 'test_env', 'name': '测试环境'},
]
