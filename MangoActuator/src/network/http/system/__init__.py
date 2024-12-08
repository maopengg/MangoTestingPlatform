# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:13
# @Author : 毛鹏
from .database import Database
from .index import Index
from .notice import Notice
from .tasks import Tasks
from .tasks_details import TasksList
from .test_suite import TestSuite
from .test_suite_details import TestSuiteDetails
from .time import TimeTasks
from .cache_data import CacheData
from .file_data import FileData
from .test_object import TestObject
from .project import Project
from .product import Product
from .module import Module


class SystemApi(
    Database,
    Notice,
    TasksList,
    Tasks,
    TestSuite,
    TestSuiteDetails,
    Index,
    TimeTasks,
    CacheData,
    FileData,
    TestObject,
    Project,
    Product,
    Module,
):
    pass
