# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-07-25 上午11:56
# @Author : 毛鹏
from pydantic import ValidationError

from src.auto_test.auto_system.models import Database, TestObject
from src.enums.tools_enum import AutoTypeEnum
from src.exceptions import *
from mangokit import MysqlConingModel


def func_mysql_config(test_object_id: int) -> MysqlConingModel:
    """
    获取mysql的配置信息生成model
    @param test_object_id:
    @return:
    """
    try:
        mysql = Database.objects.get(test_object=test_object_id)
    except Database.DoesNotExist:
        raise SystemEError(*ERROR_MSG_0021)
    except Database.MultipleObjectsReturned:
        raise SystemEError(*ERROR_MSG_0056)
    try:
        return MysqlConingModel(
            host=mysql.host,
            port=mysql.port,
            user=mysql.user,
            password=mysql.password,
            database=mysql.name)
    except ValidationError:
        raise SystemEError(*ERROR_MSG_0022)


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
        raise SystemEError(*ERROR_MSG_0046)
    except TestObject.MultipleObjectsReturned:
        raise SystemEError(*ERROR_MSG_0049)
