# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-05 11:56
# @Author : 毛鹏
from mango_ui import THEME

search_data = [
    {
        'title': '文件名称',
        'placeholder': '请输入文件名称',
        'key': 'name',
    },
]
right_data = [
    {'name': '上传', 'theme': THEME.group.info, 'action': 'upload'}

]

table_column = [
    {
        'key': 'id',
        'name': 'ID',
        'width': 7
    },
    {
        'key': 'project',
        'name': '项目名称',
        'width': 100
    },
    {
        'key': 'name',
        'name': '文件名称',
        'width': 150
    },
    {
        'key': 'file',
        'name': '文件地址',
    },
    {
        'key': 'ope',
        'name': '操作',
        'width': 120
    },

]
table_menu = [
    {
        'name': '下载',
        'action': 'download'
    },
    {
        'name': '删除',
        'action': 'delete'
    }
]
