# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂 APP 配置

from django.apps import AppConfig


class DataFactoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.apps.data_factory'
    label = 'auto_data_factory'
