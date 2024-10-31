# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-05 11:56
# @Author : 毛鹏
from mango_ui import THEME

from src.enums.tools_enum import Status1Enum
from src.enums.ui_enum import UiPublicTypeEnum
from src.tools.methods import Methods

search_data = [
    {
        'title': 'ID',
        'placeholder': '请输入ID',
        'key': 'id',
    },
    {
        'title': '名称',
        'placeholder': '请输入名称',
        'key': 'name',
    },
    {
        'title': 'KEY',
        'placeholder': '请输入KEY名称',
        'key': 'key',
    },
]
right_data = [
    {'name': '新增', 'theme': THEME.blue, 'action': 'add'}
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
        'title': '类型',
        'placeholder': '请选择对应类型，注意不同类型的加载顺序',
        'key': 'type',
        'type': 1,
        'select': UiPublicTypeEnum.get_select()
    },
    {
        'title': '参数名称',
        'placeholder': '请输入名称',
        'key': 'name',
    },

    {
        'title': 'key',
        'placeholder': '请输入缓存的key',
        'key': 'key',
    },
    {
        'title': 'value',
        'placeholder': '请根据规则输入value值',
        'key': 'value',
    },
    {
        'title': '状态',
        'placeholder': '开启状态',
        'key': 'status',
        'type': 3,
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
        'name': '产品名称',
        'width': 100
    },
    {
        'key': 'type',
        'name': '类型',
        'width': 130,
        'option': UiPublicTypeEnum.get_option('value', 'label')
    },
    {
        'key': 'name',
        'name': '参数名称',
    },
    {
        'key': 'key',
        'name': 'key',
        'width': 50
    },
    {
        'key': 'value',
        'name': 'value',
        'width': 200
    },
    {
        'key': 'status',
        'name': '是否启用',
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
        'name': '编辑',
        'action': 'edit'
    },
    {
        'name': '删除',
        'action': 'delete'
    }

]
