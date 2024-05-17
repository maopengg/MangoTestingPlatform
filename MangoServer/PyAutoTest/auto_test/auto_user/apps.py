# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description:
# @Time   : 2023/1/17 10:20
# @Author : 毛鹏
import logging

from django.apps import AppConfig

log = logging.getLogger('system')


class AutoUserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'PyAutoTest.auto_test.auto_user'

    def ready(self):
        pass
