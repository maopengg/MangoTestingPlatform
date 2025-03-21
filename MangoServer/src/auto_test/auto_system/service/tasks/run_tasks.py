# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023/3/24 17:33
# @Author : 毛鹏
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.auto_test.auto_system.models import Tasks, TasksDetails, TimeTasks
from src.auto_test.auto_system.service.tasks.add_tasks import AddTasks
from src.enums.tools_enum import StatusEnum, TestCaseTypeEnum
from src.tools.decorator.retry import orm_retry


class RunTasks:
    scheduler = BackgroundScheduler()

    @classmethod
    def create_jobs(cls):
        queryset = TimeTasks.objects.all()
        for timer in queryset:
            if timer.cron:
                cls.scheduler.add_job(
                    cls.timing,
                    trigger=CronTrigger.from_crontab(timer.cron),
                    args=[timer.id]
                )
        cls.scheduler.start()
        atexit.register(cls.scheduler.shutdown)

    @classmethod
    @orm_retry('timing')
    def timing(cls, timing_strategy_id):
        scheduled_tasks_obj = Tasks.objects.filter(timing_strategy=timing_strategy_id,
                                                   status=StatusEnum.SUCCESS.value)
        for scheduled_tasks in scheduled_tasks_obj:
            cls.distribute(scheduled_tasks)

    @classmethod
    @orm_retry('trigger')
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
            if task.type == TestCaseTypeEnum.API.value:
                add_tasks.add_test_suite_details(task.api_case.id, TestCaseTypeEnum.API)
            elif task.type == TestCaseTypeEnum.UI.value:
                add_tasks.add_test_suite_details(task.ui_case.id, TestCaseTypeEnum.UI)
            else:
                add_tasks.add_test_suite_details(task.pytest_case.id, TestCaseTypeEnum.PYTEST)
