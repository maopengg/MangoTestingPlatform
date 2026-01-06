# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023/3/24 17:33
# @Author : 毛鹏
import atexit
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.auto_test.auto_system.models import Tasks, TasksDetails, TimeTasks
from src.auto_test.auto_system.service.tasks.add_tasks import AddTasks
from src.enums.tools_enum import StatusEnum, TestCaseTypeEnum
from src.tools.decorator.retry import async_task_db_connection
from src.tools.log_collector import log


class RunTasks:
    scheduler = BackgroundScheduler()

    @classmethod
    def create_jobs(cls):
        # 多进程保护机制，防止在多进程环境下重复执行
        if cls._is_duplicate_process():
            log.system.debug("不在主进程中，跳过定时任务初始化")
            return

        queryset = TimeTasks.objects.all()
        for timer in queryset:
            if timer.cron:
                cls.scheduler.add_job(
                    cls.timing,
                    trigger=CronTrigger.from_crontab(timer.cron),
                    args=[timer.id],
                    id=f'timing_task_{timer.id}'  # 添加任务ID以支持后续管理
                )
                log.system.debug(f'设置的定时任务：{timer.name},cron:{timer.cron}')
        cls.scheduler.start()

        def _shutdown_scheduler():
            # 解释器退出阶段避免再提交线程任务，降低 RuntimeError 风险
            try:
                if getattr(cls.scheduler, "running", False):
                    cls.scheduler.shutdown(wait=False)
            except Exception:
                pass

        atexit.register(_shutdown_scheduler)

    @classmethod
    def _is_duplicate_process(cls):
        """
        检查是否为重复进程，防止在多进程环境下重复执行
        """
        # 检查是否为重载进程
        run_main = os.environ.get('RUN_MAIN', None)
        if run_main != 'true':
            return True

        # 检查DJANGO环境变量
        django_settings = os.environ.get('DJANGO_SETTINGS_MODULE')
        if not django_settings:
            return True

        return False

    @classmethod
    @async_task_db_connection()
    def timing(cls, timing_strategy_id):
        log.system.debug(f'触发定时器：{timing_strategy_id}')
        scheduled_tasks_obj = Tasks.objects.filter(timing_strategy=timing_strategy_id,
                                                   status=StatusEnum.SUCCESS.value)
        for scheduled_tasks in scheduled_tasks_obj:
            log.system.debug(f'触发任务：{scheduled_tasks}')
            cls.distribute(scheduled_tasks)

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
