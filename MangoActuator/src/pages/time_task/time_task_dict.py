# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-10-15 14:54
# @Author : 毛鹏
from mango_ui import THEME

from src.enums.system_enum import EnvironmentEnum, AutoTestTypeEnum
from src.enums.tools_enum import Status1Enum
from src.network import HTTP

search_data = [
    {
        'title': 'ID',
        'placeholder': '请输入页面ID',
        'key': 'id',
    },
    {
        'title': '任务名称',
        'placeholder': '请输入任务名称',
        'key': 'name',
    },

]

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
        'title': 'Cron表达式',
        'placeholder': '请选择周期',
        'key': 'cron',
    },
    {
        'title': '自动化类型',
        'placeholder': '请选择自动化类型',
        'key': 'type',
        'type': 1,
        'select': AutoTestTypeEnum.get_select()
    },
    {
        'title': '测试环境',
        'placeholder': '请选择自动化定时环境',
        'key': 'test_env',
        'type': 1,
        'select': EnvironmentEnum.get_select()

    },
    {
        'title': '负责人',
        'placeholder': '请选择定时任务负责人',
        'key': 'case_people',
        'type': 1,
        'select': HTTP.get_nickname
    },
    {
        'title': '执行器',
        'placeholder': '请选择执行器来执行用例',
        'key': 'case_executor',
        'type': 4,
        'select': HTTP.get_nickname
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
        'name': '任务名称',
    }, {
        'key': 'cron',
        'name': 'cron',
    },
    {
        'key': 'type',
        'name': '任务类型',
        'width': 140,
        'option': AutoTestTypeEnum.get_option('value', 'label')

    }, {
        'key': 'test_env',
        'name': '测试环境',
        'width': 100,
        'option': EnvironmentEnum.get_option('value', 'label')

    },
    {
        'key': 'case_people',
        'name': '负责人',
        'width': 100

    },
    {
        'key': 'case_executor',
        'name': '执行器',
        'width': 180

    },
    {
        'key': 'status',
        'name': '状态',
        'width': 70,
        'option': Status1Enum.get_option('value', 'label')

    },
    {
        'key': 'is_notice',
        'name': '通知',
        'width': 70,
        'option': Status1Enum.get_option('value', 'label')

    },
    {
        'key': 'ope',
        'name': '操作',
        'width': 120
    },

]
table_menu = [
    {
        'name': '触发',
        'action': 'run'
    },
    {
        'name': '添加',
        'action': 'subpage'
    },
    {
        'name': '···',
        'action': '',
        'son': [
            {
                'name': '编辑',
                'action': 'edit'
            },
            {
                'name': '删除',
                'action': 'delete'
            }
        ]
    }
]
