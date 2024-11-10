# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-05 11:56
# @Author : 毛鹏
from mango_ui import THEME, ComboBoxDataModel
from src.enums.ui_enum import BrowserTypeEnum, DeviceEnum

web_h5_data = [ComboBoxDataModel(id=i, name=i) for i in DeviceEnum.get_obj()]
web_h5_data.insert(0, ComboBoxDataModel(id=None, name='默认非H5'))

right_data = [
    {'name': '新增WEB', 'theme': THEME.group.info, 'action': 'add_web'},
    {'name': '新增安卓', 'theme': THEME.group.info, 'action': 'add_android'}
]

web_form_data = [
    {
        'title': '最大化',
        'placeholder': '是否开启浏览器最大化',
        'key': 'web_max',
        'required': False,
        'type': 3
    },
    {
        'title': '无头',
        'placeholder': '是否开启无头模式',
        'key': 'web_headers',
        'required': False,
        'type': 3
    },
    {
        'title': '录制',
        'placeholder': '是否开启浏览器录制',
        'key': 'web_recording',
        'required': False,
        'type': 3
    },
    {
        'title': '类型',
        'placeholder': '请选择需要启动的浏览器',
        'key': 'web_type',
        'select': BrowserTypeEnum.get_select(),
        'type': 1,
    },
    {
        'title': '并行数',
        'placeholder': '请选择需要并发的数量',
        'key': 'web_parallel',
        'select': [ComboBoxDataModel(id=index, name=index) for index in ["1", "2", "3", "5", "10", "15", "20", "30"]],
        'type': 1
    },
    {
        'title': '启动路径',
        'placeholder': '请输入浏览器路径',
        'key': 'web_path',
        'required': False,

    },
    {
        'title': 'H5模式',
        'placeholder': '请选择浏览器启动模式',
        'key': 'web_h5',
        'type': 1,
        'select': web_h5_data,
        'required': False,
    },
]
android_form_data = [
    {
        'title': '设备号',
        'placeholder': '请输入安卓设备号',
        'key': 'and_equipment',
    },

]
