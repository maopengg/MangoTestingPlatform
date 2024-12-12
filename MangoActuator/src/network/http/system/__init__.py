# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:13
# @Author : 毛鹏
from .cache_data import CacheData
from .database import Database
from .file_data import FileData
from .index import Index
from .module import Module
from .notice import Notice
from .product import Product
from .project import Project
from .tasks import Tasks
from .tasks_details import TasksDetails
from .test_object import TestObject
from .test_suite import TestSuite
from .test_suite_details import TestSuiteDetails
from .time import Time


class SystemApi:
    test_object = TestObject
    database = Database
    notice = Notice
    tasks = Tasks
    tasks_details = TasksDetails
    test_suite = TestSuite
    test_suite_details = TestSuiteDetails
    index = Index
    time = Time
    cache_data = CacheData
    file_data = FileData
    project = Project
    product = Product
    module = Module
