# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023/3/24 17:33
# @Author : 毛鹏
import atexit
import os
import sys
import logging
import apscheduler.events
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.auto_test.auto_system.models import Tasks, TasksDetails, TimeTasks
from src.auto_test.auto_system.service.tasks.add_tasks import AddTasks
from src.enums.tools_enum import StatusEnum, TestCaseTypeEnum
from src.tools.decorator.retry import async_task_db_connection
from src.tools.log_collector import log


class SchedulerErrorFilter(logging.Filter):
    """过滤调度器关闭时的正常错误"""
    def filter(self, record):
        error_msg = str(record.getMessage()).lower()
        # 过滤掉服务关闭时的正常错误
        if any(keyword in error_msg for keyword in [
            'cannot schedule new futures after shutdown',
            'cannot schedule new futures after interpreter shutdown',
            'after shutdown'
        ]):
            return False  # 不记录这些错误
        return True


class RunTasks:
    scheduler = None
    
    @classmethod
    def _error_listener(cls, event):
        """调度器错误监听器"""
        if event.exception:
            error_msg = str(event.exception).lower()
            # 忽略服务关闭时的错误
            if any(keyword in error_msg for keyword in ['cannot schedule', 'after shutdown', 'interpreter shutdown']):
                # 这些错误在服务关闭时是正常的，静默忽略
                return
            # 其他错误记录日志
            log.system.error(f'调度器执行任务时发生错误: {event.exception}')
            import traceback
            traceback.print_exc()
    
    @classmethod
    def _get_scheduler(cls):
        """获取或创建调度器实例"""
        if cls.scheduler is None:
            # 配置调度器，使用 daemon 线程，这样在服务关闭时能够更快退出
            cls.scheduler = BackgroundScheduler(daemon=True)
            # 添加错误监听器，监听任务执行错误
            cls.scheduler.add_listener(
                cls._error_listener, 
                apscheduler.events.EVENT_JOB_ERROR | apscheduler.events.EVENT_JOB_EXECUTED
            )
            # 配置 APScheduler 的日志记录器，过滤关闭时的正常错误
            scheduler_logger = logging.getLogger('apscheduler')
            scheduler_logger.addFilter(SchedulerErrorFilter())
        return cls.scheduler
    
    @classmethod
    def shutdown_scheduler(cls):
        """关闭调度器"""
        try:
            if cls.scheduler and cls.scheduler.running:
                # 先暂停调度器，停止接受新任务
                cls.scheduler.pause()
                # 移除所有任务
                try:
                    cls.scheduler.remove_all_jobs()
                except Exception:
                    pass  # 忽略移除任务时的错误
                # 然后关闭调度器，不等待任务完成（因为可能已经在关闭过程中）
                try:
                    cls.scheduler.shutdown(wait=False)
                except RuntimeError as e:
                    # 如果调度器已经在关闭过程中，忽略错误
                    error_msg = str(e).lower()
                    if 'shutdown' not in error_msg:
                        raise
                cls.scheduler = None
                log.system.info('RunTasks 调度器已关闭')
        except Exception as e:
            log.system.error(f'关闭 RunTasks 调度器异常: {e}')
            import traceback
            traceback.print_exc()
            # 即使出错也重置调度器
            cls.scheduler = None

    @classmethod
    def create_jobs(cls):
        try:
            scheduler = cls._get_scheduler()
            
            # 如果调度器已经在运行，先关闭它（避免重复启动）
            if scheduler.running:
                log.system.warning('调度器已在运行，先关闭再重新创建')
                try:
                    scheduler.pause()
                    scheduler.remove_all_jobs()
                    scheduler.shutdown(wait=False)
                except Exception:
                    pass  # 忽略关闭时的错误
                # 创建新的调度器实例
                cls.scheduler = BackgroundScheduler(daemon=True)
                cls.scheduler.add_listener(
                    cls._error_listener, 
                    apscheduler.events.EVENT_JOB_ERROR | apscheduler.events.EVENT_JOB_EXECUTED
                )
                # 配置 APScheduler 的日志记录器，过滤关闭时的正常错误
                scheduler_logger = logging.getLogger('apscheduler')
                scheduler_logger.addFilter(SchedulerErrorFilter())
                scheduler = cls.scheduler
            
            queryset = TimeTasks.objects.all()
            for timer in queryset:
                if timer.cron:
                    scheduler.add_job(
                        cls.timing,
                        trigger=CronTrigger.from_crontab(timer.cron),
                        args=[timer.id],
                        id=f'timing_{timer.id}',
                        replace_existing=True,  # 如果任务已存在则替换
                    )
                    log.system.debug(f'设置的定时任务：{timer.name},cron:{timer.cron}')
            scheduler.start()
            log.system.info('定时任务调度器启动成功')
        except Exception as e:
            log.system.error(f'创建定时任务异常: {e}')
            import traceback
            traceback.print_exc()

    @classmethod
    @async_task_db_connection()
    def timing(cls, timing_strategy_id):
        try:
            log.system.debug(f'触发定时器：{timing_strategy_id}')
            scheduled_tasks_obj = Tasks.objects.filter(timing_strategy=timing_strategy_id,
                                                       status=StatusEnum.SUCCESS.value)
            for scheduled_tasks in scheduled_tasks_obj:
                log.system.debug(f'触发任务：{scheduled_tasks}')
                cls.distribute(scheduled_tasks)
        except RuntimeError as e:
            # 捕获调度器关闭时的错误（服务关闭或重新加载时常见）
            error_msg = str(e).lower()
            if 'cannot schedule new futures after shutdown' in error_msg or 'after shutdown' in error_msg:
                log.system.debug(f'调度器已关闭，忽略定时任务执行: {e}')
                return
            # 其他 RuntimeError 重新抛出
            raise
        except Exception as e:
            log.system.error(f'执行定时任务异常: {e}')
            import traceback
            traceback.print_exc()

    @classmethod
    def trigger(cls, scheduled_tasks_id):
        scheduled_tasks = Tasks.objects.get(id=scheduled_tasks_id)
        cls.distribute(scheduled_tasks)

    @classmethod
    def distribute(cls, tasks: Tasks):
        tasks_details = TasksDetails.objects.filter(task=tasks.id)
        add_tasks = AddTasks(
            project_product=tasks.project_product.id,
            test_env=tasks.test_env,
            is_notice=tasks.is_notice,
            user_id=tasks.case_people.id,
            tasks_id=tasks.id,
        )
        for task in tasks_details:
            log.system.debug(f'触发任务开始执行：{task.id}')
            if task.type == TestCaseTypeEnum.API.value:
                add_tasks.add_test_suite_details(task.api_case.id, TestCaseTypeEnum.API)
            elif task.type == TestCaseTypeEnum.UI.value:
                add_tasks.add_test_suite_details(task.ui_case.id, TestCaseTypeEnum.UI)
            else:
                add_tasks.add_test_suite_details(task.pytest_case.id, TestCaseTypeEnum.PYTEST)
