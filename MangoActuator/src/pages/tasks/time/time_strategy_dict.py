# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-10-15 14:54
# @Author : 毛鹏
from mango_ui import THEME

search_data = [
    {
        'title': 'ID',
        'placeholder': '请输入ID',
        'key': 'id',
    },
    {
        'title': '策略名称',
        'placeholder': '请输入策略名称',
        'key': 'name',
    },

]

right_data = [
    {'name': '新增', 'theme': THEME.blue, 'action': 'add'}

]
form_data = [
    {
        'title': '策略名称',
        'placeholder': '请输入策略名称',
        'key': 'name',
    },
    {
        'title': 'Cron表达式',
        'placeholder': '请输入Cron表达式',
        'key': 'cron',
    },

]
table_column = [
    {
        'key': 'id',
        'name': 'ID',
        'width': 7
    },
    {
        'key': 'create_time',
        'name': '创建时间',
    },
    {
        'key': 'name',
        'name': '策略名称',
    },
    {
        'key': 'cron',
        'name': 'cron表达式',
    },
    {
        'key': 'ope',
        'name': '操作',
        'width': 120
    },
]
table_menu = [
    {
        'name': '编辑',
        'action': 'edit'
    },
    {
        'name': '删除',
        'action': 'delete'
    }
]
