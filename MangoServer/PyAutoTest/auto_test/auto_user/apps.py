# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023/1/17 10:20
# @Author : 毛鹏
import logging
import os
import threading

import time
from django.apps import AppConfig

log = logging.getLogger('system')


class AutoUserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'PyAutoTest.auto_test.auto_user'

    def ready(self):
        def run():
            time.sleep(5)
            self.new_user()

        if os.environ.get('RUN_MAIN', None) == 'true':
            task1 = threading.Thread(target=run)
            task1.start()

    def new_user(self):
        from PyAutoTest.settings import INIT_MANGO_TESTING_PLATFORM
        if INIT_MANGO_TESTING_PLATFORM:
            from PyAutoTest.auto_test.auto_user.models import Role
            if not Role.objects.exists():
                Role.objects.create(name="项目管理员", description="我是超管，嘻嘻~")
                Role.objects.create(name="研发部经理", description="研发部经理")
                Role.objects.create(name="开发经理", description="开发经理")
                Role.objects.create(name="测试经理", description="测试经理")
                Role.objects.create(name="产品经理", description="产品经理")
                Role.objects.create(name="开发组长", description="开发组长")
                Role.objects.create(name="测试组长", description="测试组长")
                Role.objects.create(name="开发工程师", description="开发工程师")
                Role.objects.create(name="测试开发工程师", description="测试开发工程师")
                Role.objects.create(name="自动化工程师", description="自动化工程师")
                Role.objects.create(name="测试工程师", description="测试工程师")
            from PyAutoTest.auto_test.auto_user.models import User
            if not User.objects.exists():
                User.objects.create(
                    nickname="admin",
                    username="admin",
                    password="e10adc3949ba59abbe56e057f20f883e",
                    role=0
                )
