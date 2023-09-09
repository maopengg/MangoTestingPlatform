# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-07-12 17:03
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_api.models import ApiCase, ApiPublic
from PyAutoTest.auto_test.auto_system.models import TestObject, Database
from PyAutoTest.enums.api_enum import ApiPublicTypeEnum
from PyAutoTest.models.api_data_model import ApiPublicModel, RequestModel
from PyAutoTest.models.system_data_model import MysqlDBModel


class GetCommonParameters:

    @classmethod
    def get_args(cls, test_obj_id) -> list[ApiPublicModel]:
        """
        获取公共数据
        @param test_obj_id:
        @return:
        """
        data = []
        test_obj = TestObject.objects.get(id=test_obj_id)
        for i in ApiPublic.objects.filter(
                project_id=test_obj.project_id).order_by('public_type'):
            if i.public_type == ApiPublicTypeEnum.LOGIN.value:
                case = ApiCase.objects.get(id=i.value)
                url = test_obj.value + case.url
                i.value = RequestModel(case_id=case.id,
                                       case_name=case.name,
                                       url=url,
                                       method=case.method,
                                       header=case.header,
                                       body_type=case.body_type,
                                       body=case.body).json()
            data.append(ApiPublicModel.from_orm(i))
        return data
        # return [ApiPublicModel.from_orm(i) for i in
        #         ApiPublic.objects.filter(
        #             project_id=TestObject.objects.get(id=test_obj_id).project_id).order_by('public_type')]
        # data = []
        # for i in ApiPublic.objects.filter(
        #         project_id=TestObject.objects.get(id=test_obj_id).project_id).order_by('public_type'):
        #     if i.public_type == ApiPublicTypeEnum.LOGIN.value:
        #         i.value = ApiCase.objects.get(id=i.value)
        #     data.append(ApiPublicModel(**i))
        # return data

    @classmethod
    def get_mysql_config(cls, test_obj_id: int) -> MysqlDBModel:
        """
        获取mysql的配置参数
        @param test_obj_id:
        @return:
        """
        mysql = Database.objects.get(test_obj_id=test_obj_id)
        if mysql:
            return MysqlDBModel(
                host=mysql.host,
                port=mysql.post,
                user=mysql.user,
                password=mysql.password,
                db=mysql.name)
        raise "改项目未配置mysql"
