# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-07-30 上午11:41
# @Author : 毛鹏
from django.core.management.base import BaseCommand
from django.utils import timezone
from PyAutoTest.auto_test.auto_ui.models import UiCase
import threading
from django.core.management.base import BaseCommand
from django.utils import timezone
from croniter import croniter
import threading

def execute_task(cron_expression):
    # 在这里执行你的任务
    print(f"执行任务: {cron_expression}")

class Command(BaseCommand):
    help = '每分钟检查 Cron 表达式'

    def handle(self, *args, **kwargs):
        current_time = timezone.now()
        records = UiCase.objects.all()  # 获取所有记录

        for record in records:
            print(record.name)
            # cron_expression = record.cron  # 假设你的模型有一个 cron 字段
            # cron = croniter(cron_expression, current_time)
            #
            # # 检查当前时间是否符合 Cron 表达式
            # if cron.get_next() == current_time:
            #     threading.Thread(target=execute_task, args=(cron_expression,)).start()

        print(f"扫描时间: {current_time}")
