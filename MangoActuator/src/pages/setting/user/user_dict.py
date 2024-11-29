# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-05 11:56
# @Author : 毛鹏
from src.network import HTTP

search_data = [
    {
        'title': 'ID',
        'placeholder': '请输入用户ID',
        'key': 'id',
    },
    {
        'title': '昵称',
        'placeholder': '请输入用户昵称',
        'key': 'name',
    },
    {
        'title': '账号',
        'placeholder': '请输入用户账号',
        'key': 'username',
    }
]
# right_data = [
#     {'name': '新增', 'theme': THEME.group.info, 'action': 'add'}
#
# ]
form_data = [
    {
        'title': '昵称',
        'placeholder': '请输入用户昵称',
        'key': 'name',
    },
    {
        'title': '绑定角色',
        'placeholder': '请选择用户角色',
        'key': 'role',
        'type': 1,
        'select': HTTP.get_role_name
    },
    {
        'title': 'mailbox',
        'placeholder': '请输入邮箱',
        'key': 'mailbox',
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
        'name': '昵称',
        'width': 100
    },

    {
        'key': 'username',
        'name': '账号',
        'width': 70
    },
    {
        'key': 'role',
        'name': '角色',
        'width': 100
    },
    {
        'key': 'last_login_time',
        'name': '最近登录时间',
        'width': 150
    }, {
        'key': 'ip',
        'name': '登录IP',
        'width': 150
    }, {
        'key': 'mailbox',
        'name': '邮箱',
    },
    {
        'key': 'ope',
        'name': '操作',
        'width': 120
    }
]
table_menu = [
    {
        'name': '编辑',
        'action': 'edit'
    },

]
