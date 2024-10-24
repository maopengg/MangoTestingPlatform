# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-10-24 17:03
# @Author : 毛鹏
from src.enums.system_enum import EnvironmentEnum, AutoTestTypeEnum

table_column = [
    {
        'key': 'id',
        'name': 'ID',
        'width': 7
    },
    {
        'key': 'name',
        'name': '任务名称',
    },
    {
        'key': 'type',
        'name': '任务类型',
        'width': 140,
        'option': AutoTestTypeEnum.get_option('value', 'label')

    },
    {
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
]
