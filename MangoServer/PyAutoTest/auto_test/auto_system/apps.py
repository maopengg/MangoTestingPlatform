# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description:
# @Time   : 2023/1/17 10:20
# @Author : 毛鹏

import logging
import threading

import time
from django.apps import AppConfig
from django.db import ProgrammingError, OperationalError

log = logging.getLogger('system')


class AutoSystemConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'PyAutoTest.auto_test.auto_system'

    def ready(self):
        def delayed_task():
            time.sleep(10)
            try:
                from PyAutoTest.auto_test.auto_system.service.scheduled_tasks.tasks import Tasks
                Tasks.create_jobs()
            except OperationalError:
                pass
            except RuntimeError:
                pass
            except ProgrammingError:
                log.error(
                    '请先迁移数据库再运行服务！！！如果正在迁移请忽略~')
                raise Exception(
                    '请先迁移数据库再运行服务！！！如果正在迁移请忽略~')

        delayed_thread = threading.Thread(target=delayed_task)
        delayed_thread.start()
