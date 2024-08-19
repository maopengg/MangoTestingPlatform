# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description:
# @Time   : 2023/1/17 10:20
# @Author : 毛鹏
import os
import threading

import time
from apscheduler.schedulers.background import BackgroundScheduler
from django.apps import AppConfig
from django.db import ProgrammingError, OperationalError

from PyAutoTest.enums.system_enum import CacheDataKeyEnum
from PyAutoTest.tools.log_collector import log


class AutoSystemConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'PyAutoTest.auto_test.auto_system'

    def ready(self):
        def run():
            time.sleep(5)
            self.minute_task()
            self.delayed_task()
            self.save_cache()

        if os.environ.get('RUN_MAIN', None) == 'true':
            task1 = threading.Thread(target=run)
            task1.start()

    @staticmethod
    def minute_task():
        from PyAutoTest.auto_test.auto_system.service.scheduled_tasks.scan_table import mytask
        sched = BackgroundScheduler()
        sched.add_job(mytask, 'interval', seconds=60)
        sched.start()

    @staticmethod
    def delayed_task():
        try:
            from PyAutoTest.auto_test.auto_system.service.scheduled_tasks.tasks import Tasks
            Tasks.create_jobs()
        except OperationalError:
            pass
        except RuntimeError:
            pass
        except ProgrammingError:
            log.system.error('请先迁移数据库再运行服务！！！如果正在迁移请忽略~')
            raise Exception('请先迁移数据库再运行服务！！！如果正在迁移请忽略~')

    @staticmethod
    def save_cache():
        from PyAutoTest.auto_test.auto_system.views.cache_data import CacheDataSerializers, CacheData
        key_list = [{'describe': i.value, 'key': i.name} for i in CacheDataKeyEnum]
        for key in key_list:
            try:
                CacheData.objects.get(key=key.get('key'))
            except CacheData.DoesNotExist:
                for i, value in CacheDataKeyEnum.obj().items():
                    if i == key.get('key') and value:
                        key['value'] = value
                serializer = CacheDataSerializers(data=key)
                if serializer.is_valid():
                    serializer.save()
