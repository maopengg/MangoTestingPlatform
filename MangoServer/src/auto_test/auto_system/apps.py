# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023/1/17 10:20
# @Author : 毛鹏
import os
import threading
import traceback
from datetime import timedelta

import atexit
import time
from apscheduler.schedulers.background import BackgroundScheduler
from django.apps import AppConfig
from django.utils import timezone
from mangotools.decorator import func_info
from mangotools.enums import CacheValueTypeEnum

from src.enums.system_enum import CacheDataKeyEnum
from src.enums.tools_enum import TaskEnum, StatusEnum
from src.settings import RETRY_FREQUENCY
from src.tools.decorator.retry import async_task_db_connection
from src.tools.log_collector import log
from django.db import transaction


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
            required_tasks = [
                {"name": "每1分钟触发", "cron": "*/1 * * * *"},
                {"name": "每3分钟触发", "cron": "*/3 * * * *"},
                {"name": "每5分钟触发", "cron": "*/5 * * * *"},
                {"name": "每10分钟触发", "cron": "*/10 * * * *"},
                {"name": "每20分钟触发", "cron": "*/20 * * * *"},
                {"name": "每30分钟触发", "cron": "*/30 * * * *"},
                {"name": "每1小时触发", "cron": "0 * * * *"},
                {"name": "每2小时触发", "cron": "0 */2 * * *"},
                {"name": "每3小时触发", "cron": "0 */3 * * *"},
                {"name": "每4小时触发", "cron": "0 */4 * * *"},
                {"name": "每5小时触发", "cron": "0 */5 * * *"},
                {"name": "每6小时触发", "cron": "0 */6 * * *"},
                {"name": "每天1点触发", "cron": "0 1 * * *"},
                {"name": "每天5点触发", "cron": "0 5 * * *"},
                {"name": "每天8点触发", "cron": "0 8 * * *"},
                {"name": "每天9点触发", "cron": "0 9 * * *"},
                {"name": "每天10点触发", "cron": "0 10 * * *"},
                {"name": "每天12点触发", "cron": "0 12 * * *"},
                {"name": "每天14点触发", "cron": "0 14 * * *"},
                {"name": "每天16点触发", "cron": "0 16 * * *"},
                {"name": "每天17点触发", "cron": "0 17 * * *"},
                {"name": "每天18点触发", "cron": "0 18 * * *"},
                {"name": "每天19点触发", "cron": "0 19 * * *"},
                {"name": "每天22点触发", "cron": "0 22 * * *"},
                {"name": "每天9点，14点，17点触发", "cron": "0 9,14,17 * * *"},
                {"name": "每天早上9点-晚上7点每小时触发", "cron": "0 9-19 * * *"},
                {"name": "每周一8点触发", "cron": "0 8 * * 1"},
            ]

            existing_crons = set(TimeTasks.objects.values_list('cron', flat=True))
            missing_tasks = [task for task in required_tasks if task['cron'] not in existing_crons]

            if missing_tasks:
                # 创建不存在的定时任务配置
                time_tasks_to_create = [
                    TimeTasks(name=task['name'], cron=task['cron'])
                    for task in missing_tasks
                ]

                created_count = len(time_tasks_to_create)
                TimeTasks.objects.bulk_create(time_tasks_to_create, ignore_conflicts=True)
                log.system.info(f'成功创建 {created_count} 个缺失的定时任务配置')
            else:
                log.system.info('所有定时任务配置已存在，跳过初始化')
        except Exception as e:
            log.system.error(f'初始化定时任务配置失败: {e}')
            # 重新抛出异常，让调用者知道初始化失败
            raise

    def shutdown(self):
        # 不再需要停止消费者线程，因为不再启动它
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

            # 添加任务状态检查任务，每3分钟执行一次
            self.scheduler.add_job(
                self.check_task_status,
                'interval',
                minutes=3,
                id='check_task_status'
            )

            self.scheduler.start()
            atexit.register(self.stop_scheduler)
        except Exception as e:
            log.system.error(f'定时任务调度器设置异常: {e}')

    @async_task_db_connection()
    def check_task_status(self):
        """检查所有任务状态，每3分钟执行一次"""
        from src.auto_test.auto_system.service.notice import NoticeMain

        reset_time = 30
        try:
            # 检查全部执行完，没有修改测试套结果的，和没有发送测试报告的
            from src.auto_test.auto_system.models import TestSuiteDetails, TestSuite
            test_suite = TestSuite.objects.filter(status__in=[TaskEnum.PROCEED.value, TaskEnum.STAY_BEGIN.value])
            for i in test_suite:
                status_list = TestSuiteDetails \
                    .objects \
                    .filter(test_suite=i).values_list('status', flat=True)
                if TaskEnum.STAY_BEGIN.value not in status_list and TaskEnum.PROCEED.value not in status_list:
                    if TaskEnum.FAIL.value in status_list:
                        i.status = TaskEnum.FAIL.value
                    else:
                        i.status = TaskEnum.SUCCESS.value
                    i.save()
                if i.is_notice != StatusEnum.SUCCESS.value and i.tasks is not None and i.tasks.notice_group and i.tasks.is_notice == StatusEnum.SUCCESS.value:
                    if (i.tasks.fail_notice == StatusEnum.SUCCESS.value and i.status != StatusEnum.SUCCESS.value) or i.tasks.fail_notice != StatusEnum.SUCCESS.value:
                        log.system.info(f'通过定时任务发送通知：{i.pk}')
                        NoticeMain.notice_main(i.tasks.notice_group_id, i.pk)
                        i.is_notice = StatusEnum.SUCCESS.value
                        i.save()

            # 把进行中的，修改为待开始,或者失败
            test_suite_details_list = TestSuiteDetails \
                .objects \
                .filter(status=TaskEnum.PROCEED.value, retry__lt=RETRY_FREQUENCY + 1)
            for test_suite_detail in test_suite_details_list:
                if test_suite_detail.push_time and (
                        timezone.now() - test_suite_detail.push_time > timedelta(minutes=reset_time)):
                    test_suite_detail.status = TaskEnum.STAY_BEGIN.value
                    test_suite_detail.save()
                    log.system.info(
                        f'推送时间超过{reset_time}分钟，状态重置为：待执行，用例ID：{test_suite_detail.case_id}')

            # 把重试次数满的，修改为0，只有未知错误才会设置为失败
            test_suite_details_list = TestSuiteDetails \
                .objects \
                .filter(status__in=[TaskEnum.PROCEED.value, TaskEnum.STAY_BEGIN.value],
                        retry__gte=RETRY_FREQUENCY + 1)
            for test_suite_detail in test_suite_details_list:
                if test_suite_detail.push_time and (
                        timezone.now() - test_suite_detail.push_time > timedelta(minutes=reset_time)):
                    test_suite_detail.status = TaskEnum.FAIL.value
                    test_suite_detail.save()
                    log.system.info(
                        f'重试次数超过{RETRY_FREQUENCY + 1}次的任务状态重置为：失败，用例ID：{test_suite_detail.case_id}')

        except Exception as e:
            log.system.error(f'检查任务状态时发生异常: {e}')
            import traceback
            traceback.print_exc()

    def stop_scheduler(self):
        """停止调度器"""
        try:
            if hasattr(self, 'scheduler') and self.scheduler and getattr(self.scheduler, 'running', False):
                self.scheduler.shutdown()
        except Exception as e:
            traceback.print_exc()
            log.system.error(f'停止调度器异常: {e}')

    @async_task_db_connection()
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

        # 确保事务提交
        transaction.commit()
