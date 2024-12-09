# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-10-15 14:54
# @Author : 毛鹏
from mango_ui import THEME

from src.enums.tools_enum import Status5Enum, EnvironmentEnum, AutoTestTypeEnum
from src.network import HTTP
from src.tools.methods import Methods

search_data = [
    {
        'title': 'ID',
        'placeholder': '请输入ID',
        'key': 'id',
    },
    {
        'title': '任务名称',
        'placeholder': '请输入任务名称',
        'key': 'name',
    },

]

right_data = [
    {'name': '新增', 'theme': THEME.group.info, 'action': 'add'}

]
form_data = [
    {
        'title': '项目/产品',
        'placeholder': '请选择项目产品',
        'key': 'project_product',
        'type': 2,
        'select': Methods.get_product_module_cascader_model,

    },
    {
        'title': '任务名称',
        'placeholder': '请输入任务名称',
        'key': 'name',
    },
    {
        'title': '定时策略',
        'placeholder': '请选择定时策略',
        'key': 'timing_strategy',
        'type': 1,
        'select': HTTP.system.time.system_time_name
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
        'select': HTTP.user.info.get_name
    },
    {
        'title': '状态',
        'placeholder': '请选择状态',
        'key': 'status',
        'type': 3,
        'select': Status5Enum.get_select()
    },
    {
        'title': '通知状态',
        'placeholder': '请选择通知状态',
        'key': 'is_notice',
        'type': 3,
        'select': Status5Enum.get_select()

    },
]
table_column = [
    {
        'key': 'id',
        'name': 'ID',
        'width': 7
    },
    {
        'key': 'project_product',
        'name': '项目',
    },
    {
        'key': 'name',
        'name': '任务名称',
    },
    {
        'key': 'timing_strategy',
        'name': '定时策略',
        'width': 150,
    },
    {
        'key': 'type',
        'name': '任务类型',
        'width': 80,
        'option': AutoTestTypeEnum.get_option('value', 'label')

    },
    {
        'key': 'test_env',
        'name': '测试环境',
        'width': 80,
        'option': EnvironmentEnum.get_option('value', 'label')
    },
    {
        'key': 'case_people',
        'name': '负责人',
        'width': 70

    },
    {
        'key': 'status',
        'name': '状态',
        'width': 50,
        'option': Status5Enum.get_option('value', 'label')

    },
    {
        'key': 'is_notice',
        'name': '通知',
        'width': 50,
        'option': Status5Enum.get_option('value', 'label')
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
