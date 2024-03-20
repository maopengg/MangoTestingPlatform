# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description:
# @Time   : 2023/1/17 10:20
# @Author : 毛鹏
import logging
import threading

import time
from django.apps import AppConfig
from django.db.utils import ProgrammingError, OperationalError

log = logging.getLogger('system')


class AutoUserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'PyAutoTest.auto_test.auto_user'

    def ready(self):
        def delayed_task():
            time.sleep(10)
            try:
                from PyAutoTest.auto_test.auto_user.service.files_crud import FilesCRUD
                FilesCRUD().initialization()
            except OperationalError:
                pass
            except ProgrammingError:
                log.error('如果您是在迁移数据库时报错请忽略报错继续迁移。您还未迁移数据库！请先初始化数据库后再操作。迁移数据库之前，请先清空PyAutoTet/auto_test/auto_{*}/migrations目录的所有文件')
                raise Exception('如果您是在迁移数据库时报错请忽略报错继续迁移。您还未迁移数据库！请先初始化数据库后再操作。迁移数据库之前，请先清空PyAutoTet/auto_test/auto_{*}/migrations目录的所有文件')

        delayed_thread = threading.Thread(target=delayed_task)
        delayed_thread.start()
