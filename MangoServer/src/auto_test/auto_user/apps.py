# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023/1/17 10:20
# @Author : 毛鹏
import os
import threading

import time
from django.apps import AppConfig

from src.tools.log_collector import log
from src.enums.system_enum import SocketEnum


class AutoUserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.auto_test.auto_user'

    def ready(self):
        # 多进程保护机制，防止在多进程环境下重复执行
        if self._is_duplicate_process():
            return
            
        if os.getenv('DJANGO_ENV', 'master') == 'master':
            self.check_version()

        def run():
            time.sleep(10)
            self.new_role()
            self.new_user()

        task1 = threading.Thread(target=run)
        task1.start()

    def _is_duplicate_process(self):
        """
        检查是否为重复进程，防止在多进程环境下重复执行
        """
        # 检查是否为重载进程
        run_main = os.environ.get('RUN_MAIN', None)
        if run_main != 'true':
            return True
            
        # 检查DJANGO环境变量
        django_settings = os.environ.get('DJANGO_SETTINGS_MODULE')
        if not django_settings:
            return True
            
        return False

    def new_role(self):
        try:
            from src.auto_test.auto_user.models import Role
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
        except Exception as error:
            log.system.error(f'角色创建失败: {error}')

    def new_user(self):
        try:
            from src.auto_test.auto_user.models import User
            from mangotools.data_processor import EncryptionTool
            user, created = User.objects.get_or_create(
                username=SocketEnum.OPEN.value,
                defaults={
                    'name': SocketEnum.OPEN.value,
                    'password': EncryptionTool.md5_32_small('123456'),
                    'mailbox': [],
                    'config': {}
                }
            )
        except Exception as error:
            log.system.error(f'用户创建失败: {error}')

    def check_version(self):
        import re
        import requests
        from src.settings import VERSION
        text = requests.get('https://gitee.com/mao-peng/MangoTestingPlatform').text
        match = re.search(r'VERSION\s*=\s*([\d.]+)', text)
        if not (match and match.group(1) == VERSION):
            raise Exception(
                f'当前版本与最新不一致，请执行git pull 升级到最新版本！最新版本：{match.group(1)}，当前版本：{VERSION}')