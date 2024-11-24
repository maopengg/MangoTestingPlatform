# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023/3/24 17:33
# @Author : 毛鹏
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from PyAutoTest.auto_test.auto_system.models import Tasks, TasksDetails, TimeTasks
from PyAutoTest.auto_test.auto_system.service.scheduled_tasks.add_tasks import AddTasks
from PyAutoTest.enums.system_enum import AutoTestTypeEnum
from PyAutoTest.enums.tools_enum import StatusEnum
from PyAutoTest.tools.decorator.retry import orm_retry
from PyAutoTest.tools.log_collector import log


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
        if tasks.type == AutoTestTypeEnum.API.value:
            tasks_details = TasksDetails.objects.filter(task=tasks.id)
            add_tasks = AddTasks(
                project=tasks.project.id,
                test_env=tasks.test_env,
                is_notice=tasks.is_notice,
                user_id=tasks.case_people.id,
                _type=AutoTestTypeEnum.API.value,
                tasks_id=tasks.id,
            )
            add_tasks.add_test_suite_details([tasks.case_id for tasks in tasks_details])
        elif tasks.type == AutoTestTypeEnum.UI.value:
            tasks_details = TasksDetails.objects.filter(task=tasks.id)
            add_tasks = AddTasks(
                project=tasks.project.id,
                test_env=tasks.test_env,
                is_notice=tasks.is_notice,
                user_id=tasks.case_people.id,
                _type=AutoTestTypeEnum.UI.value,
                tasks_id=tasks.id,
            )
            add_tasks.add_test_suite_details([tasks.case_id for tasks in tasks_details])

        else:
            log.system.error('开始执行性能自动化任务')
