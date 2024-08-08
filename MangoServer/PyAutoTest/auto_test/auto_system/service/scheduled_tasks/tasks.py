# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023/3/24 17:33
# @Author : 毛鹏
import logging
from threading import Thread

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from PyAutoTest.auto_test.auto_api.service.api_call.api_case import ApiCaseRun
from PyAutoTest.auto_test.auto_system.models import ScheduledTasks, TasksRunCaseList, TimeTasks
from PyAutoTest.auto_test.auto_ui.service.ui_test_run import UiTestRun
from PyAutoTest.enums.system_enum import AutoTestTypeEnum
from PyAutoTest.enums.tools_enum import StatusEnum
from PyAutoTest.exceptions import MangoServerError
from PyAutoTest.tools.decorator.retry import orm_retry

log = logging.getLogger('system')


class Tasks:
    scheduler = BackgroundScheduler()

    @classmethod
    def create_jobs(cls):
        queryset = TimeTasks.objects.all()
        for timer in queryset:
            cls.scheduler.add_job(cls.timing,
                                  trigger=CronTrigger(month=timer.month,
                                                      day=timer.day,
                                                      day_of_week=timer.day_of_week,
                                                      hour=timer.hour,
                                                      minute=timer.minute),
                                  args=[timer.id])
        cls.scheduler.start()

    @classmethod
    @orm_retry('timing')
    def timing(cls, timing_strategy_id):
        log.info(f'开始执行任务ID为：{timing_strategy_id}的用例')
        # 执行数据库查询操作

        scheduled_tasks_obj = ScheduledTasks.objects.filter(timing_strategy=timing_strategy_id,
                                                            status=StatusEnum.SUCCESS.value)
        for scheduled_tasks in scheduled_tasks_obj:
            cls.distribute(scheduled_tasks)

    @classmethod
    @orm_retry('trigger')
    def trigger(cls, scheduled_tasks_id):
        scheduled_tasks = ScheduledTasks.objects.get(id=scheduled_tasks_id)
        if scheduled_tasks.type == AutoTestTypeEnum.API.value:
            cls.api_task(
                scheduled_tasks_id=scheduled_tasks.id,
                test_env=scheduled_tasks.test_env,
                is_notice=scheduled_tasks.is_notice,
                user_obj={'id': scheduled_tasks.case_people.id, 'username': scheduled_tasks.case_people.username},
                is_trigger=True)
        elif scheduled_tasks.type == AutoTestTypeEnum.UI.value:
            cls.ui_task(scheduled_tasks.id,
                        scheduled_tasks.case_people.id,
                        scheduled_tasks.test_env,
                        scheduled_tasks.is_notice,
                        scheduled_tasks.case_executor,
                        True)
        else:
            log.error('开始执行性能自动化任务')

    @classmethod
    def distribute(cls, scheduled_tasks):
        # scheduled_tasks: ScheduledTasks = scheduled_tasks
        if scheduled_tasks.type == AutoTestTypeEnum.API.value:
            task = Thread(
                target=cls.api_task,
                args=(scheduled_tasks.id,
                      scheduled_tasks.test_env,
                      scheduled_tasks.is_notice,
                      {'id': scheduled_tasks.case_people.id, 'username': scheduled_tasks.case_people.username}
                      )
            )
            task.start()

        elif scheduled_tasks.type == AutoTestTypeEnum.UI.value:
            task = Thread(target=cls.ui_task, args=(scheduled_tasks.id,
                                                    scheduled_tasks.case_people.id,
                                                    scheduled_tasks.test_env,
                                                    scheduled_tasks.is_notice,
                                                    scheduled_tasks.case_executor
                                                    ))
            task.start()
        else:
            log.error('开始执行性能自动化任务')

    @classmethod
    @orm_retry('api_task')
    def api_task(cls,
                 scheduled_tasks_id: int,
                 test_env: int,
                 is_notice: int,
                 user_obj: dict,
                 is_trigger: bool = False):
        try:

            run_case = TasksRunCaseList.objects.filter(task=scheduled_tasks_id).order_by('sort')
            case_id_list = [case.case for case in run_case]
            if case_id_list:
                log.info(f'定时任务开始执行API用例，包含用例ID：{case_id_list}')

                ApiCaseRun(test_env, is_notice=is_notice, user_obj=user_obj).case_batch(
                    case_id_list)
        except MangoServerError as error:
            log.error(f'执行API定时任务失败，错误消息：{error.msg}')
            if is_trigger:
                raise error

    @classmethod
    @orm_retry('ui_task')
    def ui_task(cls,
                scheduled_tasks_id: int,
                user_id: int,
                test_env: int,
                is_notice: int,
                case_executor: list,
                is_trigger: bool = False,
                ):
        try:

            run_case = TasksRunCaseList.objects.filter(task=scheduled_tasks_id).order_by('sort')
            case_id_list = [case.case for case in run_case]
            if case_id_list:
                log.info(f'定时任务开始执行UI用例，包含用例ID：{case_id_list}')
                UiTestRun(
                    user_id=user_id,
                    test_env=test_env,
                    case_executor=case_executor,
                    tasks_id=scheduled_tasks_id,
                    is_notice=is_notice,
                ).case_batch(case_id_list)
        except MangoServerError as error:
            log.error(f'执行UI定时任务失败，错误消息：{error.msg}')
            if is_trigger:
                raise error
