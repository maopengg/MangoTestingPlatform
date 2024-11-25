# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:13
# @Author : 毛鹏
from .database import Database
from .home import Home
from .notice import Notice
from .tasks import ScheduledTasks
from .tasks_details import TasksList
from .test_suite import TestSuite
from .test_suite_details import TestSuiteDetails
from .time_tasks import TimeTasks
from .cache_data import CacheData


class SystemApi(
    Database,
    Notice,
    TasksList,
    ScheduledTasks,
    TestSuite,
    TestSuiteDetails,
    Home,
    TimeTasks,
    CacheData,
):
    pass
