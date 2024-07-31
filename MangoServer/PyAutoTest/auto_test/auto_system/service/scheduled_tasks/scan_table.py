# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-07-30 上午11:41
# @Author : 毛鹏
from apscheduler.schedulers.background import BackgroundScheduler
import time
sched = BackgroundScheduler()

@sched.scheduled_job('interval', seconds=30)  # 表示间隔一分钟会执行函数
def mytask():
    print(f'{time.time()}次要任务')
