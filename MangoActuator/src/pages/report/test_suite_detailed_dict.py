# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-05 11:56
# @Author : 毛鹏
from mango_ui import THEME

right_data = [
    {'name': '返回', 'theme': THEME.group.warning, 'action': 'back'}
]
field_list = [
    {'key': 'id', 'name': '测试套ID'},
    {'key': 'project_product', 'name': '项目名称'},
    {'key': 'create_time', 'name': '执行时间'},
    {'key': 'status', 'name': '测试结果'},
    {'key': 'test_env', 'name': '测试环境'},
    {'key': 'run_status', 'name': '执行状态'},
    {'key': 'error_message', 'name': '失败消息'},
]
