# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-10-15 14:54
# @Author : 毛鹏
from mango_ui import THEME

right_data = [
    {'name': '新增', 'theme': THEME.blue, 'action': 'add'}

]
form_data = [
    {
        'title': '任务名称',
        'placeholder': '请输入任务名称',
        'key': 'name',
    },
    {
        'title': '循环周期',
        'placeholder': '请选择周期',
        'key': 'cycle',
        'type': 4
    },
    {
        'title': '循环时间',
        'placeholder': '请选择循环时间',
        'key': 'time',
        'type': 1
    },
    {
        'title': '自动化类型',
        'placeholder': '请选择自动化类型',
        'key': 'type',
        'type': 1
    },
    {
        'title': '测试环境',
        'placeholder': 'environment',
        'key': 'test_env',
        'type': 1
    },
    {
        'title': '负责人',
        'placeholder': '请选择定时任务负责人',
        'key': 'case_people',
        'type': 1
    },
    {
        'title': '执行器',
        'placeholder': '请选择执行器来执行用例',
        'key': 'case_executor',
        'type': 5
    },
]
table_column = [
    {
        'key': 'id',
        'name': 'ID',
        'width': 7
    },
    {
        'key': 'name',
        'name': '角色名称',
        'width': 300
    },

    {
        'key': 'description',
        'name': '角色描述',
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
