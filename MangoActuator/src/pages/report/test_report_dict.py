# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-10-24 17:10
# @Author : 毛鹏
from src.enums.system_enum import EnvironmentEnum
from src.enums.tools_enum import Status3Enum

search_data = [
    {
        'title': 'ID',
        'placeholder': '请输入ID',
        'key': 'id',
    },
    {
        'title': '测试结果',
        'placeholder': '请选择测试结果',
        'key': 'status',
        'type': 1,
        'select': Status3Enum.get_select()
    },
    {
        'title': '自动化类型',
        'placeholder': '请选择自动化类型',
        'key': 'type',
        'type': 1,
        'select': EnvironmentEnum.get_select()
    }
]
table_column = [
    {
        'key': 'id',
        'name': 'ID',
        'width': 100
    },
    {
        'key': 'project_product',
        'name': '项目/产品',
        'item': 'name',
        'width': 100
    },
    {
        'key': 'test_env',
        'name': '测试环境',
        'width': 70,
        'option': EnvironmentEnum.get_option('value', 'label')
    },
    {
        'key': 'create_time',
        'name': '执行时间',
        'width': 150
    },
    {
        'key': 'user',
        'name': '执行人',
        'width': 70
    },
    {
        'key': 'run_status',
        'name': '执行状态',
        'width': 70,
        'option': Status3Enum.get_option('value', 'label')

    },
    {
        'key': 'status',
        'name': '结果',
        'width': 70,
        'option': Status3Enum.get_option('value', 'label')
    },
    {
        'key': 'error_message',
        'name': '失败提示',
    },
    {
        'key': 'ope',
        'name': '操作',
        'width': 50
    },

]
table_menu = [
    {
        'name': '详情',
        'action': 'subpage'
    }
]
