# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023/1/17 10:20
# @Author : 毛鹏
import threading
from datetime import timedelta

import atexit
import time
from apscheduler.schedulers.background import BackgroundScheduler
from django.apps import AppConfig
from django.db import transaction
from django.utils import timezone
from mangotools.decorator import func_info
from mangotools.enums import CacheValueTypeEnum

from src.enums.system_enum import CacheDataKeyEnum, TestSuiteNoticeEnum
from src.enums.tools_enum import TaskEnum
from src.settings import RETRY_FREQUENCY
from src.tools import is_main_process
from src.tools.decorator.retry import async_task_db_connection
from src.tools.log_collector import log


class AutoSystemConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.auto_test.auto_system'

    def ready(self):
        # 多进程保护机制，防止在多进程环境下重复执行
        if is_main_process(lock_name='mango_system_init', logger=log.system):
            return

        def run():
            try:
                time.sleep(10)
                self.delayed_task()
                self.save_cache()
                self.populate_time_tasks()
                self.init_ass()

                # 设置定时任务调度器
                self.setup_scheduler()
            except (RuntimeError, SystemError) as e:
                # 忽略进程关闭时的错误（开发服务器重载时常见）
                error_msg = str(e).lower()
                if any(keyword in error_msg for keyword in
                       ['shutdown', 'interpreter', 'cannot schedule', 'after shutdown']):
                    log.system.debug(f'系统模块：忽略进程关闭错误: {e}')
                    return
                log.system.error(f'系统模块初始化异常: {e}')
            except Exception as e:
                log.system.error(f'系统模块初始化异常: {e}')
                import traceback
                traceback.print_exc()

        # 启动后台任务（设置为 daemon 线程，确保在服务关闭时能够快速退出）
        task1 = threading.Thread(target=run, daemon=True)
        task1.start()
        # 只在主进程中注册退出处理函数，避免在开发服务器重载时被意外触发
        # 使用模块级别的标志确保只注册一次
        if not hasattr(AutoSystemConfig, '_shutdown_registered'):
            atexit.register(self.shutdown)
            AutoSystemConfig._shutdown_registered = True

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
        # 停止 RunTasks 调度器
        try:
            from src.auto_test.auto_system.service.tasks.run_tasks import RunTasks
            RunTasks.shutdown_scheduler()
        except Exception as e:
            log.system.error(f'关闭 RunTasks 调度器异常: {e}')

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
            # 创建调度器实例（使用 daemon 线程，确保在服务关闭时能够快速退出）
            self.scheduler = BackgroundScheduler(daemon=True)

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
            # 只在主进程中注册退出处理函数，避免在开发服务器重载时被意外触发
            # 使用模块级别的标志确保只注册一次
            if not hasattr(AutoSystemConfig, '_scheduler_shutdown_registered'):
                atexit.register(self.stop_scheduler)
                AutoSystemConfig._scheduler_shutdown_registered = True
        except Exception as e:
            log.system.error(f'定时任务调度器设置异常: {e}')

    @async_task_db_connection()
    def check_task_status(self):
        """检查所有任务状态，每3分钟执行一次"""
        try:
            from src.auto_test.auto_system.service.test_suite.send_notice import SendNotice

            reset_time = 30
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
            test_suite = TestSuite.objects.filter(is_notice=TestSuiteNoticeEnum.NOT_SENT.value, status__in=[TaskEnum.SUCCESS.value, TaskEnum.FAIL.value])
            for i in test_suite:
                try:
                    SendNotice(i.id).send_test_suite()
                except Exception:
                    pass
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

        except (RuntimeError, SystemError) as e:
            # 忽略进程关闭时的错误（开发服务器重载时常见）
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in
                   ['shutdown', 'interpreter', 'cannot schedule', 'after shutdown']):
                log.system.debug(f'检查任务状态时忽略关闭错误: {e}')
                return
            log.system.error(f'检查任务状态时发生异常: {e}')
            import traceback
            traceback.print_exc()
        except Exception as e:
            log.system.error(f'检查任务状态时发生异常: {e}')
            import traceback
            traceback.print_exc()

    def stop_scheduler(self):
        """停止调度器"""
        try:
            if hasattr(self, 'scheduler') and self.scheduler and getattr(self.scheduler, 'running', False):
                self.scheduler.shutdown(wait=False)  # 不等待，快速关闭
        except (RuntimeError, SystemError) as e:
            # 忽略关闭时的正常错误
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in
                   ['shutdown', 'interpreter', 'cannot schedule', 'after shutdown']):
                return
            log.system.debug(f'停止调度器时忽略错误: {e}')
        except Exception as e:
            log.system.error(f'停止调度器异常: {e}')

    @async_task_db_connection()
    def set_case_status(self):
        try:
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
        except (RuntimeError, SystemError) as e:
            # 忽略进程关闭时的错误（开发服务器重载时常见）
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in
                   ['shutdown', 'interpreter', 'cannot schedule', 'after shutdown']):
                log.system.debug(f'设置用例状态时忽略关闭错误: {e}')
                return
            log.system.error(f'设置用例状态时发生异常: {e}')
        except Exception as e:
            log.system.error(f'设置用例状态时发生异常: {e}')
