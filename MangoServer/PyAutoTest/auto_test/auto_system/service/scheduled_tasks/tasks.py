# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023/3/24 17:33
# @Author : 毛鹏
import logging
from threading import Thread

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from PyAutoTest.auto_test.auto_api.models import ApiCase
from PyAutoTest.auto_test.auto_api.service.test_runner.api_test_run import ApiTestRun
from PyAutoTest.auto_test.auto_system.models import ScheduledTasks, TasksRunCaseList, TimeTasks
from PyAutoTest.auto_test.auto_ui.data_producer.ui_test_run import UiTestRun
from PyAutoTest.enums.system_enum import AutoTestTypeEnum
from PyAutoTest.enums.tools_enum import StatusEnum
from PyAutoTest.exceptions import MangoServerError

log = logging.getLogger('system')


class Tasks:
    scheduler = BackgroundScheduler()

    @classmethod
    def api_task(cls, scheduled_tasks_id: int, test_obj_id: int, is_notice: bool):
        try:
            run_case = TasksRunCaseList.objects.filter(task=scheduled_tasks_id)
            case_id_list = [case.case for case in run_case]
            if case_id_list:
                log.info(f'定时任务开始执行API用例，包含用例ID：{case_id_list}')
                project_id = ApiCase.objects.get(id=case_id_list[0]).project.id
                ApiTestRun(project_id=project_id, test_obj_id=test_obj_id, is_notice=is_notice).case_batch(case_id_list)
        except MangoServerError as error:
            log.error(f'执行API定时任务失败，错误消息：{error.msg}')

    @classmethod
    def ui_task(cls, scheduled_tasks_id: int, user_id: int, test_obj_id: int, is_notice: bool):
        try:
            run_case = TasksRunCaseList.objects.filter(task=scheduled_tasks_id)
            case_id_list = [case.case for case in run_case]
            if case_id_list:
                log.info(f'定时任务开始执行UI用例，包含用例ID：{case_id_list}')
                UiTestRun(user_id=user_id, test_obj_id=test_obj_id, is_timing=True, is_notice=is_notice).case_batch(
                    case_id_list)
        except MangoServerError as error:
            log.error(f'执行UI定时任务失败，错误消息：{error.msg}')

    @classmethod
    def distribute(cls, task_id):
        log.info(f'开始执行任务ID为：{task_id}的用例')
        scheduled_tasks = ScheduledTasks.objects.filter(timing_strategy=task_id, status=StatusEnum.SUCCESS.value)
        for i in scheduled_tasks:
            # scheduled_tasks: ScheduledTasks = scheduled_tasks
            is_notice = True if i.is_notice == StatusEnum.SUCCESS.value else False
            if i.type == AutoTestTypeEnum.API.value:
                task = Thread(target=cls.api_task, args=(i.id, i.test_obj.id, is_notice))
                task.start()

            elif i.type == AutoTestTypeEnum.UI.value:
                task = Thread(target=cls.ui_task, args=(i.id, i.executor_name.id, i.test_obj.id, is_notice))
                task.start()
            else:
                log.error('开始执行性能自动化任务')

    @classmethod
    def create_jobs(cls):
        queryset = TimeTasks.objects.all()
        for timer in queryset:
            cls.scheduler.add_job(cls.distribute,
                                  trigger=CronTrigger(month=timer.month,
                                                      day=timer.day,
                                                      day_of_week=timer.day_of_week,
                                                      hour=timer.hour,
                                                      minute=timer.minute),
                                  args=[timer.id])
        cls.scheduler.start()


Tasks.create_jobs()
