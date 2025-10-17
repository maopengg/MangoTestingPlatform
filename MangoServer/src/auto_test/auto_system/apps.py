# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023/1/17 10:20
# @Author : 毛鹏
import os
import threading
from datetime import timedelta

import atexit
import time
from apscheduler.schedulers.background import BackgroundScheduler
from django.apps import AppConfig
from django.utils import timezone
from mangotools.decorator import func_info
from mangotools.enums import CacheValueTypeEnum

from src.enums.system_enum import CacheDataKeyEnum
from src.enums.tools_enum import TaskEnum
from src.tools.decorator.retry import ensure_db_connection
from src.tools.log_collector import log


class AutoSystemConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.auto_test.auto_system'

    def ready(self):
        def run():
            time.sleep(10)
            self.delayed_task()
            self.save_cache()
            self.populate_time_tasks()
            self.run_tests()
            self.init_ass()
            self.start_consumer()

        if os.environ.get('RUN_MAIN', None) == 'true':
            task1 = threading.Thread(target=run)
            task1.start()
        atexit.register(self.shutdown)

    @staticmethod
    def delayed_task():
        try:
            from src.auto_test.auto_system.service.tasks.run_tasks import RunTasks
            RunTasks.create_jobs()
        except Exception as e:
            log.system.error(f'异常提示:{e}, 首次启动项目，请启动完成之后再重启一次！')

    @staticmethod
    def save_cache():
        try:
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
        except Exception as e:
            log.system.error(f'异常提示:{e}, 首次启动项目，请启动完成之后再重启一次！')

    @staticmethod
    def populate_time_tasks():
        try:
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
                TimeTasks.objects.create(name="每天9点，14点，17点触发", cron="0 9,14,17 * * *")
                TimeTasks.objects.create(name="每周一8点触发", cron="0 8 * * 1")
        except Exception as e:
            log.system.error(f'异常提示:{e}, 首次启动项目，请启动完成之后再重启一次！')

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

    def init_ass(self):
        try:
            import json

            from src.auto_test.auto_system.models import CacheData
            from src.auto_test.auto_system.views.cache_data import CacheDataCRUD
            from src.enums.system_enum import CacheDataKey2Enum

            data = {
                'describe': CacheDataKey2Enum.ASS_SELECT_VALUE.value,
                'key': CacheDataKey2Enum.ASS_SELECT_VALUE.value,
                'value': json.dumps(func_info, ensure_ascii=False),
                'value_type': CacheValueTypeEnum.DICT.value,
            }
            try:
                cache_data = CacheData.objects.get(key=CacheDataKey2Enum.ASS_SELECT_VALUE.value)
            except CacheData.DoesNotExist:
                CacheDataCRUD.inside_post(data)
            except CacheData.MultipleObjectsReturned:
                cache_data_list = CacheData.objects.filter(key=CacheDataKey2Enum.ASS_SELECT_VALUE.value)
                for cache_data in cache_data_list:
                    cache_data.delete()
                CacheDataCRUD.inside_post(data)
            else:
                CacheDataCRUD.inside_put(cache_data.id, data)
        except Exception as e:
            log.system.error(f'异常提示:{e}, 首次启动项目，请启动完成之后再重启一次！')

    def start_consumer(self):
        scheduler = BackgroundScheduler()
        scheduler.add_job(self.set_case_status, 'interval', minutes=5)
        scheduler.start()

    @ensure_db_connection(max_retries=1)
    def set_case_status(self):
        from src.auto_test.auto_ui.models import UiCase, UiCaseStepsDetailed, PageSteps
        from src.auto_test.auto_pytest.models import PytestCase
        from src.auto_test.auto_api.models import ApiInfo, ApiCase, ApiCaseDetailed
        
        ten_minutes_ago = timezone.now() - timedelta(minutes=10)
        
        models_to_update = [
            UiCase,
            UiCaseStepsDetailed,
            PageSteps,
            PytestCase,
            ApiInfo,
            ApiCase,
            ApiCaseDetailed
        ]
        
        for model in models_to_update:
            model.objects.filter(
                status=TaskEnum.PROCEED.value,
                update_time__lt=ten_minutes_ago
            ).update(status=TaskEnum.FAIL.value)
