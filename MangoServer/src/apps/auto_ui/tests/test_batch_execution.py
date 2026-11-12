from django.test import TestCase

from src.apps.auto_ui.exceptions import (
    AutoUiError,
    UI_CASE_CASE_EXECUTION_INVALID,
)
from src.apps.auto_ui.models import UiCase
from src.apps.auto_ui.services.execution.batch_execution import UiCaseBatchExecutionService
from src.apps.test_center.models import ProductModule, Project, ProjectProduct
from src.apps.user.models import User


class UiCaseBatchProjectValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            name='UI批量执行用户',
            username='ui_batch_project_user',
            password='pwd',
            is_super_admin=True,
        )

    def create_case(self, project_name: str, product_name: str) -> UiCase:
        project = Project.objects.create(name=project_name)
        product = ProjectProduct.objects.create(project=project, name=product_name)
        module = ProductModule.objects.create(project_product=product, name=f'{product_name}模块')
        return UiCase.objects.create(
            project_product=product,
            module=module,
            name=f'{product_name}UI用例',
            case_people=self.user,
            case_flow='',
        )

    def test_cross_project_error_contains_project_names(self):
        web_case = self.create_case('Web前端项目', 'Web产品')
        app_case = self.create_case('移动端项目', 'App产品')

        with self.assertRaises(AutoUiError) as context:
            UiCaseBatchExecutionService.execute(
                case_ids=[web_case.id, app_case.id],
                test_env=0,
                user_id=self.user.id,
            )

        self.assertEqual(context.exception.code, UI_CASE_CASE_EXECUTION_INVALID.code)
        self.assertIn('Web前端项目', context.exception.msg)
        self.assertIn('移动端项目', context.exception.msg)
