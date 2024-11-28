# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-24 20:26
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_api.models import ApiCase
from PyAutoTest.auto_test.auto_system.views.test_suite_details import TestSuiteDetailsCRUD
from PyAutoTest.auto_test.auto_ui.models import UiCase
from PyAutoTest.enums.system_enum import AutoTestTypeEnum
from PyAutoTest.enums.tools_enum import TaskEnum
from PyAutoTest.tools.view import Snowflake


class AddTasks:
    def __init__(self, project_product: int, test_env: int, is_notice: int, user_id: int, _type: AutoTestTypeEnum,
                 tasks_id: int | None = None):
        self.test_suite_id = Snowflake.generate_id()
        self.project_product = project_product
        self.test_env = test_env
        self.is_notice = is_notice
        self.user_id = user_id
        self._type = _type
        self.tasks_id = tasks_id
        self.add_test_suite()

    def add_test_suite(self):
        from PyAutoTest.auto_test.auto_system.views.test_suite import TestSuiteCRUD
        TestSuiteCRUD.inside_post({
            'id': self.test_suite_id,
            'type': self._type,
            'project_product': self.project_product,
            'test_env': self.test_env,
            'user': self.user_id,
            'status': TaskEnum.STAY_BEGIN.value,
            'is_notice': self.is_notice,
            'tasks': self.tasks_id,
        })

    def add_test_suite_details(self, case_id_list: list[id]):
        for case_id in case_id_list:
            if self._type == AutoTestTypeEnum.UI.value:
                case = UiCase.objects.get(id=case_id)
            else:
                case = ApiCase.objects.get(id=case_id)
            TestSuiteDetailsCRUD.inside_post({
                'test_suite': self.test_suite_id,
                'type': self._type,
                'project_product': case.project_product.id,
                'test_env': self.test_env,
                'case_id': case_id,
                'case_name': case.name,
                'status': TaskEnum.STAY_BEGIN.value,
                'error_message': None,
                'result': None,
                'retry': 0 if self.tasks_id else 2,
            })
