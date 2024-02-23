# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-07-12 17:03
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_api.models import ApiCase, ApiPublic
from PyAutoTest.auto_test.auto_system.models import TestObject
from PyAutoTest.auto_test.auto_ui.models import UiPublic
from PyAutoTest.auto_test.auto_ui.views.ui_public import UiPublicSerializers
from PyAutoTest.enums.api_enum import ApiPublicTypeEnum
from PyAutoTest.enums.tools_enum import StatusEnum
from PyAutoTest.models.socket_model.api_model import ApiPublicModel, RequestModel
from PyAutoTest.models.socket_model.ui_model import UiPublicModel


class GetCommonParameters:

    @classmethod
    def get_api_args(cls, test_obj_id) -> list[ApiPublicModel]:
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

    @classmethod
    def get_ui_args(cls, test_obj_id) -> list[UiPublicModel]:
        """
        获取公共数据
        @param test_obj_id:
        @return:
        """
        data = []
        test_obj = TestObject.objects.get(id=test_obj_id)
        for i in UiPublic.objects.filter(project_id=test_obj.project_id, status=StatusEnum.SUCCESS.value).order_by(
                'type'):
            data.append(UiPublicSerializers(instance=i).data)
        return data
