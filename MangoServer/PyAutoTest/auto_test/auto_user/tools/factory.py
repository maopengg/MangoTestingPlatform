# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-07-25 上午11:56
# @Author : 毛鹏
from pydantic import ValidationError

from PyAutoTest.auto_test.auto_system.models import Database, TestObject
from PyAutoTest.enums.tools_enum import AutoTypeEnum
from PyAutoTest.exceptions.tools_exception import DoesNotExistError, MysqlConfigError, TestObjectNullError
from PyAutoTest.models.tools_model import MysqlConingModel
from PyAutoTest.exceptions.error_msg import ERROR_MSG_0021, ERROR_MSG_0022, ERROR_MSG_0046, ERROR_MSG_0049


def func_mysql_config(env: int, project_product_id: int) -> MysqlConingModel:
    """
    获取mysql的配置信息生成model
    @param env:
    @param project_product_id:
    @return:
    """
    try:
        mysql = Database.objects.get(environment=env, project_product=project_product_id)
    except Database.DoesNotExist:
        raise DoesNotExistError(*ERROR_MSG_0021)
    try:
        return MysqlConingModel(
            host=mysql.host,
            port=mysql.port,
            user=mysql.user,
            password=mysql.password,
            database=mysql.name)
    except ValidationError:
        raise MysqlConfigError(*ERROR_MSG_0022)


def func_test_object_value(env: int, project_product_id: int, auto_type: int) -> TestObject:
    """
    根据测试对象ID和产品ID，获取到value
    @param env:
    @param project_product_id:
    @param auto_type:
    @return:
    """
    try:
        return TestObject.objects.get(project_product=project_product_id,
                                      environment=env,
                                      auto_type__in=[auto_type, AutoTypeEnum.CURRENCY.value])
    except TestObject.DoesNotExist:
        raise TestObjectNullError(*ERROR_MSG_0046)
    except TestObject.MultipleObjectsReturned:
        raise TestObjectNullError(*ERROR_MSG_0049)
