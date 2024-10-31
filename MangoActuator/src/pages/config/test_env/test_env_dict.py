# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-05 11:56
# @Author : 毛鹏
from mango_ui import THEME

from src.enums.system_enum import EnvironmentEnum
from src.enums.tools_enum import ProductTypeEnum, Status5Enum
from src.network import HTTP
from src.tools.methods import Methods

search_data = [
    {
        'title': 'ID',
        'placeholder': '请输入ID',
        'key': 'id',
    },
    {
        'title': '环境名称',
        'placeholder': '请输入环境名称',
        'key': 'name',
    }
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
        'title': '环境名称',
        'placeholder': '请输入环境名称',
        'key': 'name',
    },
    {
        'title': '测试对象',
        'placeholder': '请输入域名/包名/路径',
        'key': 'value',
    },
    {
        'title': '部署环境',
        'placeholder': '请选择绑定环境',
        'key': 'environment',
        'type': 1,
        'select': EnvironmentEnum.get_select()
    },
    {
        'title': '自动化类型',
        'placeholder': '请选择产品的端类型',
        'key': 'auto_type',
        'type': 1,
        'select': ProductTypeEnum.get_select()
    },
    {
        'title': '负责人名称',
        'placeholder': '请输入负责人名称',
        'key': 'executor_name',
        'type': 1,
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
        'key': 'project_product',
        'name': '产品名称',
        'width': 100
    },
    {
        'key': 'name',
        'name': '环境名称',
        'width': 150
    },
    {
        'key': 'value',
        'name': '域名/包名/路径',
    },
    {
        'key': 'environment',
        'name': '部署环境',
        'width': 70,
        'option': EnvironmentEnum.get_option('value', 'label')
    },
    {
        'key': 'auto_type',
        'name': '自动化类型',
        'width': 150,
        'option': ProductTypeEnum.get_option('value', 'label')
    },
    {
        'key': 'executor_name',
        'name': '负责人',
        'width': 70
    },
    {
        'key': 'db_c_status',
        'name': '查询权限',
        'width': 70,
        'option': Status5Enum.get_option('value', 'label')
    },
    {
        'key': 'db_rud_status',
        'name': '增删改权限',
        'width': 70,
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
        'name': '环境配置',
        'action': 'subpage'
    },
    {
        'name': '删除',
        'action': 'delete'
    }
]
