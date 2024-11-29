# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023/1/17 10:20
# @Author : 毛鹏
import os
import threading
import traceback
from datetime import datetime

import time
from django.apps import AppConfig
from django.db import ProgrammingError, OperationalError

from PyAutoTest.enums.system_enum import CacheDataKeyEnum
from PyAutoTest.tools.log_collector import log
from mangokit import Mango


class AutoSystemConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'PyAutoTest.auto_test.auto_system'

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

    @staticmethod
    def delayed_task():
        try:
            from PyAutoTest.auto_test.auto_system.service.tasks.run_tasks import RunTasks
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

    @staticmethod
    def populate_time_tasks():
        from PyAutoTest.auto_test.auto_system.models import TimeTasks
        if not TimeTasks.objects.exists():
            TimeTasks.objects.create(name="每5分钟", cron="*/5 * * * *")
            TimeTasks.objects.create(name="每30分钟", cron="*/30 * * * *")
            TimeTasks.objects.create(name="每1小时", cron="0 * * * *")
            TimeTasks.objects.create(name="每2小时", cron="0 */2 * * *")
            TimeTasks.objects.create(name="每5小时", cron="0 */5 * * *")
            TimeTasks.objects.create(name="每天9点", cron="0 9 * * *")
            TimeTasks.objects.create(name="每天12点", cron="0 12 * * *")
            TimeTasks.objects.create(name="每天18点", cron="0 18 * * *")
            TimeTasks.objects.create(name="每周一8点", cron="0 8 * * 1")

    def run_tests(self):
        from PyAutoTest.auto_test.auto_system.service.consumer import consumer
        try:
            consumer()
        except RuntimeError:
            pass
        except Exception as error:
            log.system.error(error)
            trace = traceback.format_exc()
            content = f"""
               芒果测试平台管理员请注意查收:
                   触发时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                   错误函数：run_tests
                   异常类型: {type(error)}
                   错误提示: {str(error)}
                   错误详情：{trace}

               **********************************
               详细情况可前往芒果测试平台查看，非相关负责人员可忽略此消息。谢谢！

                                                             -----------芒果测试平台
               """
            from mangokit import Mango
            Mango.s(content)
            task1 = threading.Thread(target=self.run_tests)
            task1.start()
