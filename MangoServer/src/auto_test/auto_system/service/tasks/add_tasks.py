# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-24 20:26
# @Author : 毛鹏
from src.auto_test.auto_api.models import ApiCase
from src.auto_test.auto_pytest.models import PytestCase
from src.auto_test.auto_system.service.testcounter import TestCounter
from src.auto_test.auto_ui.models import UiCase
from src.enums.tools_enum import TaskEnum, TestCaseTypeEnum, StatusEnum
from src.tools.view import Snowflake


class AddTasks:
    def __init__(self, project_product: int, test_env: int, is_notice: int, user_id: int, tasks_id: int | None = None):
        self.test_suite_id = Snowflake.generate_id()
        self.project_product = project_product
        self.test_env = test_env
        self.is_notice = is_notice
        self.user_id = user_id
        self.tasks_id = tasks_id
        self.add_test_suite()

    def add_test_suite(self):
        from src.auto_test.auto_system.views.test_suite import TestSuiteCRUD
        TestSuiteCRUD.inside_post({
            'id': self.test_suite_id,
            'project_product': self.project_product,
            'test_env': self.test_env,
            'user': self.user_id,
            'status': TaskEnum.STAY_BEGIN.value,
            'is_notice': StatusEnum.FAIL.value,
            'tasks': self.tasks_id,
        })

    def add_test_suite_details(self, case_id: int, _type: TestCaseTypeEnum):
        def set_task(case_id, case_name, project_product, case_sum, parametrize=None):
            from src.auto_test.auto_system.views.test_suite_details import TestSuiteDetailsCRUD
            TestSuiteDetailsCRUD.inside_post({
                'test_suite': self.test_suite_id,
                'type': _type.value,
                'project_product': project_product,
                'test_env': self.test_env,
                'case_id': case_id,
                'case_name': case_name,
                'parametrize': parametrize if parametrize else [],
                'status': TaskEnum.STAY_BEGIN.value,
                'error_message': None,
                'result': None,
                'retry': 0 if self.tasks_id else 2,
                'case_sum': case_sum,
            })

        if _type == TestCaseTypeEnum.UI:
            case = UiCase.objects.get(id=case_id)
            if case.parametrize:
                for i in case.parametrize:
                    set_task(case.id,
                             f'{case.name} - {i.get("name")}',
                             case.project_product.id,
                             TestCounter.case_ui(case_id),
                             i.get('parametrize'))
            else:
                set_task(case.id, case.name, case.project_product.id, TestCounter.case_ui(case_id))
        elif _type == TestCaseTypeEnum.API:
            case = ApiCase.objects.get(id=case_id)

            if case.parametrize:
                for i in case.parametrize:
                    set_task(case.id,
                             f'{case.name} - {i.get("name")}',
                             case.project_product.id,
                             TestCounter.case_api(case_id),
                             i.get('parametrize'))
            else:
                set_task(case.id, case.name, case.project_product.id, TestCounter.case_api(case_id))
        else:
            case = PytestCase.objects.get(id=case_id)
            set_task(case.id, case.name, case.project_product.project_product.id, TestCounter.case_pytest(case_id))
