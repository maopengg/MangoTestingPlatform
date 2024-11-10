# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-05 11:56
# @Author : 毛鹏
from mango_ui import THEME

from src.enums.api_enum import ClientEnum, ApiPublicTypeEnum
from src.enums.tools_enum import Status5Enum
from src.tools.methods import Methods

search_data = [
    {
        'title': 'ID',
        'placeholder': '请输入ID',
        'key': 'id',
    },
    {
        'title': '名称',
        'placeholder': '请输入页面名称',
        'key': 'name',
    },
    {
        'title': '项目/产品',
        'placeholder': '请选择项目产品',
        'key': 'project_product',
        'type': 2,
        'select': Methods.get_product_module_cascader_model,
    },
    {
        'title': '客户端',
        'placeholder': '请选择客户端',
        'key': 'client',
        'type': 1,
        'select': ClientEnum.get_select()
    }
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
        'title': '客户端',
        'placeholder': '请先选择客户端类型',
        'key': 'client',
        'type': 1,
        'select': ClientEnum.get_select()
    },
    {
        'title': '类型',
        'placeholder': '请先选择对应类型，不同类型加载顺序不一致，后面加载的可以使用前面加载的变量',
        'key': 'type',
        'type': 1,
        'select': ApiPublicTypeEnum.get_select()
    },
    {
        'title': '参数名称',
        'placeholder': '请输入参数名称',
        'key': 'name',
    },
    {
        'title': 'key',
        'placeholder': '请输入引用key',
        'key': 'key',
    },
    {
        'title': 'value',
        'placeholder': '请输入value值',
        'key': 'value',
    },
    {
        'title': '是否启用',
        'placeholder': '是否启用',
        'key': 'status',
        'type': 3
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
        'key': 'client',
        'name': '客户端',
        'width': 100,
        'option': ClientEnum.get_option('value', 'label')

    },
    {
        'key': 'type',
        'name': '类型',
        'width': 100,
        'option': ApiPublicTypeEnum.get_option('value', 'label')

    },
    {
        'key': 'name',
        'name': '页面名称',
        'width': 150
    },
    {
        'key': 'key',
        'name': 'key',
        'width': 150,

    },
    {
        'key': 'value',
        'name': 'value',
    },
    {
        'key': 'status',
        'name': '状态',
        'width': 100,
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
        'name': '编辑',
        'action': 'edit'
    },
    {
        'name': '删除',
        'action': 'delete'
    }
]
