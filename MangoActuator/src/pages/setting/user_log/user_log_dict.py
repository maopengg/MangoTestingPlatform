# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-05 11:56
# @Author : 毛鹏
from src.enums.tools_enum import ClientTypeEnum

search_data = [
    {
        'title': '用户',
        'placeholder': '请选择用户',
        'key': 'user_id',
        'type': 1,
    },
    {
        'title': '来源',
        'placeholder': '请选择来源',
        'key': 'source_type',
        'type': 1,
    },

]

table_column = [
    {
        'key': 'id',
        'name': 'ID',
        'width': 50
    },
    {
        'key': 'nickname',
        'name': '昵称',
    },

    {
        'key': 'username',
        'name': '账号',
        'width': 200
    },
    {
        'key': 'source_type',
        'name': '来源',
        'width': 150,
        'option': ClientTypeEnum.get_option('value', 'label')
    },
    {
        'key': 'ip',
        'name': 'IP',
        'width': 150
    },
    {
        'key': 'create_time',
        'name': '登录时间',
        'width': 200
    },

]
