# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023/3/24 17:33
# @Author : 毛鹏
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from PyAutoTest.auto_test.auto_system.models import ScheduledTasks, TasksRunCaseList
from PyAutoTest.auto_test.auto_ui.data_producer.run_api import RunApi

logger = logging.getLogger('system')


def my_task(task_id):
    scheduled_tasks = ScheduledTasks.objects.get(id=task_id)
    run_case = TasksRunCaseList.objects.filter(task_id=task_id)
    case_id_list = [case.ui_case.id for case in run_case]
    user_dict = {'username': scheduled_tasks.executor_name.username, 'id': scheduled_tasks.executor_name.id}
    return RunApi(user_dict).case_batch(case_id_list, scheduled_tasks.test_obj.id)


# 创建定时任务的函数
def create_jobs():
    # 创建BlockingScheduler调度器
    scheduler = BackgroundScheduler()
    # 查询所有的启用的定时器数据
    queryset = ScheduledTasks.objects.filter(status=1)
    # 添加定时任务
    for task in queryset:
        timer_info = task.timing_strategy
        # 判断月、日、时、分字段是否为空，并设置相应的触发器
        if timer_info.month:
            trigger = CronTrigger(month=timer_info.month, day=timer_info.day, hour=timer_info.hour,
                                  minute=timer_info.minute, )
        elif timer_info.day:
            trigger = CronTrigger(day=timer_info.day, hour=timer_info.hour, minute=timer_info.minute)
        elif timer_info.hour:
            trigger = CronTrigger(hour=timer_info.hour, minute=timer_info.minute)
        elif timer_info.minute:
            trigger = CronTrigger(minute=timer_info.minute)
        else:
            trigger = None
            logger.error('定时器数据错误，请检查scheduled_tasks表数据')
        # 添加定时任务
        scheduler.add_job(my_task, trigger=trigger, args=[task.id])
