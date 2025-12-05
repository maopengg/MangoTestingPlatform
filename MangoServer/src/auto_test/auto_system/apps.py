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
from src.tools.decorator.retry import db_connection_context
# from src.tools.decorator.scheduler import scheduled_task, stop_scheduler
# from src.tools.decorator.retry import async_task_db_connection
from src.tools.log_collector import log


class AutoSystemConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.auto_test.auto_system'

    def ready(self):
        # 多进程保护机制，防止在多进程环境下重复执行
        if self._is_duplicate_process():
            return

        def run():
            time.sleep(10)
            self.delayed_task()
            self.save_cache()
            self.populate_time_tasks()
            self.run_tests()
            self.init_ass()
            
            # 设置定时任务调度器
            self.setup_scheduler()

        # 启动后台任务
        task1 = threading.Thread(target=run)
        task1.start()
        atexit.register(self.shutdown)

    def _is_duplicate_process(self):
        """
        检查是否为重复进程，防止在多进程环境下重复执行
        """
        # 获取当前进程ID
        pid = os.getpid()

        # 检查是否为重载进程
        run_main = os.environ.get('RUN_MAIN', None)
        if run_main != 'true':
            log.system.debug(f"跳过重复进程初始化 - PID: {pid}, RUN_MAIN: {run_main}")
            return True

        # 检查DJANGO环境变量
        django_settings = os.environ.get('DJANGO_SETTINGS_MODULE')
        if not django_settings:
            log.system.debug(f"跳过重复进程初始化 - PID: {pid}, DJANGO_SETTINGS_MODULE未设置")
            return True

        # 在Docker环境下，使用文件锁机制防止重复执行
        # 兼容Windows和Linux系统
        if os.name == 'nt':  # Windows系统
            temp_dir = os.environ.get('TEMP', os.environ.get('TMP', 'C:\\temp'))
            lock_file = f"{temp_dir}\\mango_system_init_{os.getppid()}.lock"
        else:  # Linux/Unix系统
            lock_file = f"/tmp/mango_system_init_{os.getppid()}.lock"
        try:
            # 尝试创建锁文件
            fd = os.open(lock_file, os.O_CREAT | os.O_EXCL)
            os.close(fd)
            # 注册退出时清理锁文件
            atexit.register(lambda: os.path.exists(lock_file) and os.remove(lock_file))
            log.system.debug(f"主进程初始化 - PID: {pid}")
            return False
        except FileExistsError:
            log.system.debug(f"跳过重复进程初始化 - PID: {pid}, 锁文件已存在")
            return True
        except Exception as e:
            # 如果无法创建锁文件（如权限问题），使用备用方法
            log.system.debug(f"锁文件检查异常 - PID: {pid}, 错误: {e}")
            # 检查父进程ID，避免在子进程中重复执行
            ppid = os.getppid()
            if hasattr(self, '_initialized_ppid') and self._initialized_ppid == ppid:
                return True
            self._initialized_ppid = ppid
            return False

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
        # 停止全局调度器
        self.stop_scheduler()

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

    def setup_scheduler(self):
        """设置定时任务调度器"""
        try:
            # 创建调度器实例
            self.scheduler = BackgroundScheduler()
            
            # 添加定时任务
            self.scheduler.add_job(
                self.set_case_status,
                'interval',
                minutes=5,
                id='set_case_status'
            )
            
            # 启动调度器
            self.scheduler.start()
            
            # 注册退出时停止调度器
            atexit.register(self.stop_scheduler)
        except Exception as e:
            log.system.error(f'定时任务调度器设置异常: {e}')

    def stop_scheduler(self):
        """停止调度器"""
        try:
            if hasattr(self, 'scheduler') and self.scheduler:
                self.scheduler.shutdown()
        except Exception as e:
            log.system.error(f'停止调度器异常: {e}')


    @db_connection_context()
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