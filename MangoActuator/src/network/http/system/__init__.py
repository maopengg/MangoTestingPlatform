# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:13
# @Author : 毛鹏
from .database import Database
from .home import Home
from .notice import Notice
from .scheduled_tasks import ScheduledTasks
from .tasks_list import TasksList
from .test_suite_report import TestSuiteReport
from .time_tasks import TimeTasks


class SystemApi(
    Database,
    Notice,
    TasksList,
    ScheduledTasks,
    TestSuiteReport,
    Home,
    TimeTasks
):
    pass
