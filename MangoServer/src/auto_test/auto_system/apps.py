# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023/1/17 10:20
# @Author : 毛鹏
import os
import threading

import atexit
import time
from django.apps import AppConfig
from django.db import ProgrammingError, OperationalError

from src.enums.system_enum import CacheDataKeyEnum
from src.tools.log_collector import log


class AutoSystemConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.auto_test.auto_system'

    def ready(self):
        def run():
            time.sleep(5)
            self.delayed_task()
            self.save_cache()
            self.populate_time_tasks()
            self.run_tests()

        if os.environ.get('RUN_MAIN', None) == 'true':
            task1 = threading.Thread(target=run)
            task1.start()
        atexit.register(self.shutdown)

    @staticmethod
    def delayed_task():
        try:
            from src.auto_test.auto_system.service.tasks.run_tasks import RunTasks
            RunTasks.create_jobs()
        except OperationalError:
            pass
        except RuntimeError:
            pass
        except ProgrammingError:
            log.system.error('请先迁移数据库再运行服务！！！如果正在迁移请忽略~')
            raise Exception('请先迁移数据库再运行服务！！！如果正在迁移请忽略~')

    @staticmethod
    def save_cache():
        from src.auto_test.auto_system.views.cache_data import CacheDataSerializers, CacheData
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

    @staticmethod
    def populate_time_tasks():
        from src.auto_test.auto_system.models import TimeTasks
        if not TimeTasks.objects.exists():
            TimeTasks.objects.create(name="每5分钟触发", cron="*/5 * * * *")
            TimeTasks.objects.create(name="每30分钟触发", cron="*/30 * * * *")
            TimeTasks.objects.create(name="每1小时触发", cron="0 * * * *")
            TimeTasks.objects.create(name="每2小时触发", cron="0 */2 * * *")
            TimeTasks.objects.create(name="每5小时触发", cron="0 */5 * * *")
            TimeTasks.objects.create(name="每天1点触发", cron="0 1 * * *")
            TimeTasks.objects.create(name="每天5点触发", cron="0 5 * * *")
            TimeTasks.objects.create(name="每天9点触发", cron="0 9 * * *")
            TimeTasks.objects.create(name="每天12点触发", cron="0 12 * * *")
            TimeTasks.objects.create(name="每天18点触发", cron="0 18 * * *")
            TimeTasks.objects.create(name="每天22点触发", cron="0 22 * * *")
            TimeTasks.objects.create(name="每周一8点触发", cron="0 8 * * 1")

    def run_tests(self):
        from src.auto_test.auto_system.service.consumer import ConsumerThread
        self.consumer_thread = ConsumerThread()
        self.system_task = threading.Thread(target=self.consumer_thread.consumer)
        self.system_task.daemon = True
        self.system_task.start()

    def shutdown(self):
        try:
            self.consumer_thread.stop()
            self.system_task.join()
        except AttributeError:
            pass
