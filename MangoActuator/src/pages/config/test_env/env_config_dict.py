# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-24 16:55
# @Author : 毛鹏
from mango_ui import THEME, ComboBoxDataModel
from mangokit import NoticeEnum

right_data = [
    {'name': '新增数据库', 'theme': THEME.group.info, 'action': 'add_database'},
    {'name': '新增通知', 'theme': THEME.group.info, 'action': 'add_notice'},
    {'name': '返回', 'theme': THEME.group.warning, 'action': 'back'}
]

database_form_data = [
    {
        'title': '主机',
        'placeholder': '请输入主机IP',
        'key': 'host',
    },
    {
        'title': '端口',
        'placeholder': '请输入端口',
        'key': 'port',
    },
    {
        'title': '用户名',
        'placeholder': '请输入用户名',
        'key': 'user',
    },
    {
        'title': '密码',
        'placeholder': '请输入密码',
        'key': 'password',
    },
    {
        'title': '主库',
        'placeholder': '请输入主库名称',
        'key': 'name',
    }
]
notice_form_data = [
    {
        'title': '通知类型',
        'placeholder': '请选择通知类型',
        'key': 'type',
        'type': 1,
        'select': [ComboBoxDataModel(id=str(_id), name=name) for _id, name in NoticeEnum.obj().items()],
    },
    {
        'title': '通知配置',
        'placeholder': '请输入通知配置',
        'key': 'config',
    },
]
