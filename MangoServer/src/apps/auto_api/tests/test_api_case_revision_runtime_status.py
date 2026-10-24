from types import SimpleNamespace

from django.test import TestCase
from mangotools.enums import StatusEnum
from mangotools.enums import TaskEnum

from src.apps.auto_api.models import ApiCase, ApiCaseDetailed, ApiCaseDetailedParameter, ApiInfo
from src.apps.auto_api.services.test_case.test_case import TestCase as ApiRuntimeTestCase
from src.apps.test_center.models import ProductModule, Project, ProjectProduct
from src.apps.user.models import User


class ApiCaseRevisionRuntimeStatusTests(TestCase):

    def setUp(self):
        project = Project.objects.create(name='修订状态项目')
        product = ProjectProduct.objects.create(project=project, name='主服务')
        module = ProductModule.objects.create(project_product=product, name='状态模块')
        user = User.objects.create(
            name='状态用户',
            username='api_revision_status_user',
            password='pwd',
            is_super_admin=True,
        )
        case = ApiCase.objects.create(
            project_product=product,
            module=module,
            name='修订状态用例',
            case_people=user,
            case_flow='',
        )
        api_info = ApiInfo.objects.create(
            project_product=product,
            module=module,
            name='状态接口',
            url='/status',
            method=1,
            protocol_type='http',
            body_type='none',
        )
        self.step = ApiCaseDetailed.objects.create(case=case, api_info=api_info, case_sort=1)
        self.parameter = ApiCaseDetailedParameter.objects.create(
            case_detailed=self.step,
            name='默认场景',
        )
        self.runtime = ApiRuntimeTestCase.__new__(ApiRuntimeTestCase)
        self.runtime.case_id = case.id
        self.runtime.revision_aggregate = SimpleNamespace(steps=(self.step,))

    def test_revision_execution_updates_step_status_fields(self):
        self.runtime.update_test_case_detailed_proceed(self.runtime.case_id, None)
        self.step.refresh_from_db()
        self.assertEqual(self.step.status, TaskEnum.PROCEED.value)
        self.assertIsNone(self.step.error_message)

        runtime_step = SimpleNamespace(
            id=self.step.id,
            status=StatusEnum.SUCCESS.value,
            error_message=None,
        )
        self.runtime.save_case_detailed_runtime_state(runtime_step)
        self.step.refresh_from_db()
        self.assertEqual(self.step.status, StatusEnum.SUCCESS.value)

    def test_revision_execution_updates_parameter_status_field(self):
        result = SimpleNamespace(status=StatusEnum.SUCCESS.value)
        self.runtime.update_test_case_detailed_parameter(self.parameter.id, result)
        self.parameter.refresh_from_db()
        self.assertEqual(self.parameter.status, StatusEnum.SUCCESS.value)

    def test_revision_execution_marks_unfinished_step_failed(self):
        self.runtime.update_test_case_detailed_proceed(self.runtime.case_id, None)
        self.runtime.update_test_case_detailed_unfinished(
            self.runtime.case_id,
            None,
            '执行异常',
        )
        self.step.refresh_from_db()
        self.assertEqual(self.step.status, StatusEnum.FAIL.value)
        self.assertEqual(self.step.error_message, '执行异常')
