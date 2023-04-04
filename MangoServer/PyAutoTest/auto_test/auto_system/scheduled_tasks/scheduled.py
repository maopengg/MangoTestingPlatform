# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/3/24 17:32
# @Author : 毛鹏
import datetime

from apscheduler.schedulers.blocking import BlockingScheduler


class MyScheduler:
    def __init__(self):
        self.scheduler = BlockingScheduler()

    def add_task(self, func, args, trigger_type, **trigger_args):
        self.scheduler.add_job(func, trigger_type, args=args, **trigger_args)

    def start(self):
        self.scheduler.start()


# 定义任务函数
def my_task(message):
    print(message, datetime.datetime.now())


# 创建调度器对象
scheduler = MyScheduler()
# 添加任务：自定义时间的定时任务
scheduler.add_task(my_task, ("每秒钟执行一次任务",), "interval", seconds=1, start_date="2022-12-01 00:00:00",
                   end_date="2023-01-01 00:00:00")
# 启动调度器对象
scheduler.start()
