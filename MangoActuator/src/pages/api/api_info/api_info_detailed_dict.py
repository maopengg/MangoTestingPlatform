# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-05 11:56
# @Author : 毛鹏
from mangoui import THEME

right_data = [
    {'name': '保存', 'theme': THEME.group.info, 'action': 'save'},
    {'name': '返回', 'theme': THEME.group.warning, 'action': 'back'}

]
field_list = [
    {'key': 'id', 'name': '接口ID'},
    {'key': 'name', 'name': '接口名称'},
    {'key': 'url', 'name': 'URL地址'},
    {'key': 'method', 'name': '请求方法'},

]
