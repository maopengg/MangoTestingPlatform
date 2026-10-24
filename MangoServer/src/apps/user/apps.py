# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023/1/17 10:20
# @Author : 毛鹏
import os

from django.apps import AppConfig

from src.apps.system.enums import SocketEnum
from src.common.logging import log


class UserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.apps.user'
    label = 'auto_user'

    def ready(self):
        return

    def new_role(self):
        try:
            from src.apps.user.models import Role
            if not Role.objects.exists():
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
            raise

    def new_user(self):
        try:
            from src.apps.user.models import User
            from src.apps.user.services.password import encode_plain_password
            if User.objects.exists():
                return
            default_password = encode_plain_password(os.getenv('MANGO_INITIAL_ADMIN_PASSWORD', '123456'))
            User.objects.bulk_create([
                User(
                    name='admin',
                    username='admin',
                    password=default_password,
                    config={},
                    api_key=User.unique_api_key(),
                    is_super_admin=True,
                ),
                User(
                    name=SocketEnum.OPEN.value,
                    username=SocketEnum.OPEN.value,
                    password=encode_plain_password(os.getenv('MANGO_INITIAL_GUEST_PASSWORD', '123456')),
                    config={},
                    api_key=User.unique_api_key(),
                    is_super_admin=False,
                ),
            ])
        except Exception as error:
            log.system.error(f'用户创建失败: {error}')
            raise

    def check_version(self):
        import re
        import requests
        from src.settings import VERSION
        text = requests.get('https://gitee.com/mao-peng/MangoTestingPlatform',
                            proxies={'http': None, 'https': None}).text
        match = re.search(r'VERSION\s*=\s*([\d.]+)', text)
        if not match:
            log.system.warning('警告（不影响运行）：无法从远程仓库页面解析最新版本号，请检查网络或页面内容是否变更')
            return
        if match.group(1) != VERSION:
            log.system.warning(
                f'警告（不影响运行）：当前版本与最新不一致，请执行 git pull 升级到最新版本！'
                f'最新版本：{match.group(1)}，当前版本：{VERSION}'
            )
