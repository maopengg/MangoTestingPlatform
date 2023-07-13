# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-07-12 17:03
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_api.models import ApiPublic
from PyAutoTest.auto_test.auto_system.models import TestObject
from PyAutoTest.base_data_model.api_data_model import ApiPublicModel


class GetCommonParameters:

    @classmethod
    def get_args(cls, test_obj_id) -> list[ApiPublicModel]:
        return [ApiPublicModel.from_orm(i) for i in
                ApiPublic.objects.filter(project_id=TestObject.objects.get(id=test_obj_id).project_id)]
