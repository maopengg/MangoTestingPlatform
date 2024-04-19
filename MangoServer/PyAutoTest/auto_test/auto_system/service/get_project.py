# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2022/12/30 17:46
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_system.models import TestObject


def get_host(project: int, environment: int, test_type: int) -> str:
    host = TestObject.objects.get(project=project, environment=environment, test_type=test_type).value
    return host


def get_executor(project, environment) -> str:
    name = TestObject.objects.get(project=project, environment=environment).executor_name
    return name
