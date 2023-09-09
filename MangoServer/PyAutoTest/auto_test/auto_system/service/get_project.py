# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2022/12/30 17:46
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_system.models import TestObject


def get_host(project: int, environment: int, test_type: int) -> str:
    """
        得到对应环境项目的域名
    :param project:
    :param environment:
    :param test_type:
    :return:
    """
    host = TestObject.objects.get(project=project, environment=environment, test_type=test_type).value
    return host


def get_executor(project, environment) -> str:
    """
    得到对应环境项目的负责人
    @param project: 项目名称
    @param environment: 环境变量
    @return: 负责人名称
    """
    name = TestObject.objects.get(project=project, environment=environment).executor_name
    return name
