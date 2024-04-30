# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023/3/24 17:33
# @Author : 毛鹏
import logging
from threading import Thread

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django.db import connection

from PyAutoTest.auto_test.auto_api.models import ApiCase
from PyAutoTest.auto_test.auto_api.service.test_execution.api_test_run import ApiTestRun
from PyAutoTest.auto_test.auto_system.models import ScheduledTasks, TasksRunCaseList, TimeTasks
from PyAutoTest.auto_test.auto_ui.service.ui_test_run import UiTestRun
from PyAutoTest.enums.system_enum import AutoTestTypeEnum
from PyAutoTest.enums.tools_enum import StatusEnum
from PyAutoTest.exceptions import MangoServerError
from PyAutoTest.tools.decorator.retry import retry

log = logging.getLogger('system')


class Tasks:
    scheduler = BackgroundScheduler()

    @classmethod
    def create_jobs(cls):
        connection.ensure_connection()
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
    @retry(max_retries=5, delay=5, func_name='timing')
    def timing(cls, timing_strategy_id):
        log.info(f'开始执行任务ID为：{timing_strategy_id}的用例')
        connection.ensure_connection()
        # 执行数据库查询操作

        scheduled_tasks_obj = ScheduledTasks.objects.filter(timing_strategy=timing_strategy_id,
                                                            status=StatusEnum.SUCCESS.value)
        for scheduled_tasks in scheduled_tasks_obj:
            cls.distribute(scheduled_tasks)

    @classmethod
    def trigger(cls, scheduled_tasks_id):
        connection.ensure_connection()

        scheduled_tasks = ScheduledTasks.objects.get(id=scheduled_tasks_id)
        if scheduled_tasks.type == AutoTestTypeEnum.API.value:
            cls.api_task(scheduled_tasks.id, scheduled_tasks.test_obj.id, scheduled_tasks.is_notice, True)
        elif scheduled_tasks.type == AutoTestTypeEnum.UI.value:
            cls.ui_task(scheduled_tasks.id,
                        scheduled_tasks.case_people.id,
                        scheduled_tasks.test_obj.id,
                        scheduled_tasks.is_notice,
                        scheduled_tasks.case_executor,
                        True)
        else:
            log.error('开始执行性能自动化任务')

    @classmethod
    def distribute(cls, scheduled_tasks):
        # scheduled_tasks: ScheduledTasks = scheduled_tasks
        if scheduled_tasks.type == AutoTestTypeEnum.API.value:
            task = Thread(target=cls.api_task, args=(scheduled_tasks.id,
                                                     scheduled_tasks.test_obj.id,
                                                     scheduled_tasks.is_notice))
            task.start()

        elif scheduled_tasks.type == AutoTestTypeEnum.UI.value:
            task = Thread(target=cls.ui_task, args=(scheduled_tasks.id,
                                                    scheduled_tasks.case_people.id,
                                                    scheduled_tasks.test_obj.id,
                                                    scheduled_tasks.is_notice,
                                                    scheduled_tasks.case_executor
                                                    ))
            task.start()
        else:
            log.error('开始执行性能自动化任务')
        connection.close()

    @classmethod
    def api_task(cls, scheduled_tasks_id: int, test_obj_id: int, is_notice: int, is_trigger: bool = False):
        try:
            connection.ensure_connection()

            run_case = TasksRunCaseList.objects.filter(task=scheduled_tasks_id).order_by('sort')
            case_id_list = [case.case for case in run_case]
            if case_id_list:
                log.info(f'定时任务开始执行API用例，包含用例ID：{case_id_list}')
                connection.ensure_connection()

                project_id = ApiCase.objects.get(id=case_id_list[0]).project.id
                ApiTestRun(project_id=project_id, test_obj_id=test_obj_id, is_notice=is_notice).case_batch(case_id_list)
        except MangoServerError as error:
            log.error(f'执行API定时任务失败，错误消息：{error.msg}')
            if is_trigger:
                raise error

    @classmethod
    def ui_task(cls,
                scheduled_tasks_id: int,
                user_id: int,
                test_obj_id: int,
                is_notice: int,
                case_executor: list,
                is_trigger: bool = False,
                ):
        try:
            connection.ensure_connection()

            run_case = TasksRunCaseList.objects.filter(task=scheduled_tasks_id).order_by('sort')
            case_id_list = [case.case for case in run_case]
            if case_id_list:
                log.info(f'定时任务开始执行UI用例，包含用例ID：{case_id_list}')
                UiTestRun(
                    user_id=user_id,
                    test_obj_id=test_obj_id,
                    tasks_id=scheduled_tasks_id,
                    is_notice=is_notice,
                    spare_test_object_id=test_obj_id,
                    case_executor=case_executor
                ).case_batch(case_id_list)
        except MangoServerError as error:
            log.error(f'执行UI定时任务失败，错误消息：{error.msg}')
            if is_trigger:
                raise error
