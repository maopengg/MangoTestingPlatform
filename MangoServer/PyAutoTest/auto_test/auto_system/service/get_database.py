# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-12-26 14:09
# @Author : 毛鹏
from pydantic.error_wrappers import ValidationError

from PyAutoTest.auto_test.auto_system.models import Database
from PyAutoTest.exceptions.tools_exception import DoesNotExistError, MysqlConfigError
from PyAutoTest.models.tools_model import MysqlConingModel


class GetDataBase:

    @classmethod
    def get_mysql_config(cls, test_obj_id: int) -> MysqlConingModel:
        """
        获取mysql的配置参数
        @param test_obj_id:
        @return:
        """
        try:
            mysql = Database.objects.get(test_obj_id=test_obj_id)
        except Database.DoesNotExist:
            raise DoesNotExistError('该项目未配置mysql，但是开启了数据库断言')
        try:
            return MysqlConingModel(
                host=mysql.host,
                port=mysql.port,
                user=mysql.user,
                password=mysql.password,
                db=mysql.name)
        except ValidationError:
            raise MysqlConfigError('Mysql配置错误，请先在数据库中检查mysql配置是否正确')
