# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-05-14 17:21
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_system.models import TestObject


class TestObjectGet:

    @classmethod
    def get_test_object(cls, _id: int, project_product: int) -> TestObject:
        test_object = TestObject.objects.get(id=_id)
        return TestObject.objects.get(project_product=project_product, environment=test_object.environment)
