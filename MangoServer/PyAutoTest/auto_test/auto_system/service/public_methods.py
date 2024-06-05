# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-12-26 14:09
# @Author : 毛鹏
from pydantic import ValidationError

from PyAutoTest.auto_test.auto_system.models import Database, TestObject
from PyAutoTest.exceptions.tools_exception import DoesNotExistError, MysqlConfigError, TestObjectNullError
from PyAutoTest.models.tools_model import MysqlConingModel
from PyAutoTest.tools.view.error_msg import ERROR_MSG_0021, ERROR_MSG_0022, ERROR_MSG_0046


class PublicMethods:

    @classmethod
    def get_mysql_config(cls, test_obj_id: int, real=True, project_product: int = None) -> MysqlConingModel:
        try:
            if not real and project_product:
                test_obj_id = cls.get_test_object(test_obj_id, project_product)
            test_object = TestObject.objects.get(id=test_obj_id)
            mysql = Database.objects.get(environment=test_object.environment,
                                         project_product=test_object.project_product)
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

    @classmethod
    def get_test_object(cls, _id: int, project_product: int) -> TestObject:
        try:
            test_object = TestObject.objects.get(id=_id)
            return TestObject.objects.get(project_product=project_product, environment=test_object.environment)
        except TestObject.DoesNotExist:
            raise TestObjectNullError(*ERROR_MSG_0046)
