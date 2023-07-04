# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/3/24 17:33
# @Author : 毛鹏
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from PyAutoTest.auto_test.auto_system.models import TimeTasks
from PyAutoTest.auto_test.auto_ui.data_producer.run_api import RunApi
from PyAutoTest.auto_test.auto_ui.models import UiCaseGroup

logger = logging.getLogger('system')


def my_task(task_id):
    case_group = UiCaseGroup.objects.filter(time_name=task_id)
    case_list = [i['id'] for i in case_group.values('id')]

    return RunApi().group_batch(case_list, True)


# 创建定时任务的函数
def create_jobs():
    # 创建BlockingScheduler调度器
    scheduler = BackgroundScheduler()
    # 查询所有的定时器数据
    queryset = TimeTasks.objects.all()
    # 添加定时任务
    for timer in queryset:
        # 判断月、日、时、分字段是否为空，并设置相应的触发器
        if timer.month:
            trigger = CronTrigger(month=timer.month, day=timer.day, hour=timer.hour, minute=timer.minute, )
        elif timer.day:
            trigger = CronTrigger(day=timer.day, hour=timer.hour, minute=timer.minute)
        elif timer.hour:
            trigger = CronTrigger(hour=timer.hour, minute=timer.minute)
        elif timer.minute:
            trigger = CronTrigger(minute=timer.minute)
        else:
            trigger = None
            logger.error('定时器数据错误，请检查time_tasks表数据')
        # 添加定时任务
        scheduler.add_job(my_task, trigger=trigger, args=[timer.id])
