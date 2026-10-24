from unittest.mock import patch

from django.test import TestCase

from src.apps.auto_api.exceptions import (
    API_VERSION_CASE_EXECUTION_INVALID,
    AutoApiError,
)
from src.apps.auto_api.models import ApiCase
from src.apps.auto_api.services.api_case.batch_execution import ApiCaseBatchExecutionService
from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService
from src.apps.task_center.services.selection.api_concurrency import ApiConcurrencyService
from src.apps.test_center.models import ProductModule, Project, ProjectProduct
from src.apps.user.models import User


class ApiCaseBatchProjectValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            name='批量执行用户',
            username='batch_project_user',
            password='pwd',
            is_super_admin=True,
        )

    def create_case(self, project_name: str, product_name: str) -> ApiCase:
        project = Project.objects.create(name=project_name)
        product = ProjectProduct.objects.create(project=project, name=product_name)
        module = ProductModule.objects.create(project_product=product, name=f'{product_name}模块')
        return ApiCase.objects.create(
            project_product=product,
            module=module,
            name=f'{product_name}批量执行用例',
            case_people=self.user,
            case_flow='',
        )

    @patch.object(ApiCaseRevisionService, 'resolve_batch_executions', return_value={})
    @patch.object(ApiConcurrencyService, 'resolve_report_limit', return_value=1)
    def test_cross_project_error_contains_project_names(self, _mock_limit, _mock_resolve):
        main_case = self.create_case('批量执行项目', '主服务')
        order_case = self.create_case('订单中心项目', '订单服务')

        with self.assertRaises(AutoApiError) as context:
            ApiCaseBatchExecutionService.execute(
                case_ids=[main_case.id, order_case.id],
                execution_name='跨项目批量执行',
                test_env=0,
                execution_version='editing',
                user_id=self.user.id,
            )

        self.assertEqual(context.exception.code, API_VERSION_CASE_EXECUTION_INVALID.code)
        self.assertIn('批量执行项目', context.exception.msg)
        self.assertIn('订单中心项目', context.exception.msg)
