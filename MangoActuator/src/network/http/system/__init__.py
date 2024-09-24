# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:13
# @Author : 毛鹏
from .database import Database
from .notice import Notice
from .tasks_list import TasksList
from .scheduled_tasks import ScheduledTasks
from .test_suite_report import TestSuiteReport
class System(Database, Notice, TasksList, ScheduledTasks, TestSuiteReport):
    pass