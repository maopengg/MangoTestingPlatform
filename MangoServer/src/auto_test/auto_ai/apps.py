# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: AI写用例模块
# @Author : 毛鹏
from django.apps import AppConfig


class AutoAiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.auto_test.auto_ai'
