from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from src.apps.auto_pytest.exceptions import (
    AutoPytestError,
    PYTEST_CASE_EXECUTION_INVALID,
)
from src.apps.auto_pytest.models import (
    PytestCase,
    PytestProduct,
    PytestRepository,
)
from src.apps.auto_pytest.services.execution.batch_execution import PytestCaseBatchExecutionService
from src.apps.test_center.models import (
    ProductModule,
    Project,
    ProjectProduct,
    TestSuite,
    TestSuiteDetails,
)
from src.apps.user.models import User


class PytestCaseBatchProjectValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            name='Pytest批量执行用户',
            username='pytest_batch_project_user',
            password='pwd',
            is_super_admin=True,
        )

    def create_case(self, project_name: str, product_name: str) -> PytestCase:
        project = Project.objects.create(name=project_name)
        product = ProjectProduct.objects.create(project=project, name=product_name)
        module = ProductModule.objects.create(project_product=product, name=f'{product_name}模块')
        pytest_product = PytestProduct.objects.create(
            project_product=product,
            name=f'{product_name}Pytest目录',
            file_name=f'{product_name}.py',
        )
        return PytestCase.objects.create(
            project_product=pytest_product,
            module=module,
            name=f'{product_name}Pytest用例',
            case_people=self.user,
            file_name=f'test_{product_name}.py',
            file_path=f'tests/test_{product_name}.py',
            file_update_time=timezone.now(),
        )

    def test_cross_project_error_contains_project_names(self):
        service_case = self.create_case('服务端项目', '主服务')
        data_case = self.create_case('数据项目', '数据服务')

        with self.assertRaises(AutoPytestError) as context:
            PytestCaseBatchExecutionService.execute(
                case_ids=[service_case.id, data_case.id],
                test_env=0,
                user_id=self.user.id,
            )

        self.assertEqual(context.exception.code, PYTEST_CASE_EXECUTION_INVALID.code)
        self.assertIn('服务端项目', context.exception.msg)
        self.assertIn('数据项目', context.exception.msg)

    @patch('src.apps.auto_pytest.services.execution.batch_execution.RepositoryGitService.for_product')
    def test_batch_execution_creates_report_and_detail(self, for_product_mock):
        case = self.create_case('服务端项目', '主服务')
        for_product_mock.return_value = SimpleNamespace(
            repository_file_exists=lambda _path: True,
            current_ref_info=lambda: {
                'branch': 'main',
                'commit_hash': 'a' * 40,
            },
        )

        result = PytestCaseBatchExecutionService.execute(
            case_ids=[case.id],
            test_env=0,
            user_id=self.user.id,
        )

        report = TestSuite.objects.get(id=result['test_suite_id'])
        detail = TestSuiteDetails.objects.get(test_suite=report)
        self.assertEqual(report.project_product_id, case.project_product.project_product_id)
        self.assertEqual(detail.case_id, case.id)
        self.assertEqual(detail.test_env, 0)
        self.assertEqual(result['execution_group_count'], 1)
        self.assertEqual(result['execution_groups'][0]['case_ids'], [case.id])

    @patch('src.apps.auto_pytest.services.execution.batch_execution.RepositoryGitService.for_product')
    def test_same_project_cases_from_two_repositories_are_split_into_groups(self, for_product_mock):
        project = Project.objects.create(name='统一业务项目')
        repositories = [
            PytestRepository.objects.create(
                name=f'仓库{index}',
                provider='gitlab',
                repo_url=f'https://example.com/team/repository-{index}.git',
                remote_project=f'team/repository-{index}',
                default_branch='main',
            )
            for index in (1, 2)
        ]
        cases = []
        for index, repository in enumerate(repositories, start=1):
            product = ProjectProduct.objects.create(project=project, name=f'产品{index}')
            module = ProductModule.objects.create(project_product=product, name=f'模块{index}')
            pytest_project = PytestProduct.objects.create(
                project_product=product,
                repository=repository,
                name=f'Pytest项目{index}',
                file_name='tests',
                test_dir=['.'],
            )
            cases.append(PytestCase.objects.create(
                project_product=pytest_project,
                module=module,
                name=f'同名用例{index}',
                case_people=self.user,
                file_name='test_auth.py',
                file_path='tests/test_auth.py',
                file_update_time=timezone.now(),
            ))

        def git_service(pytest_project):
            repository_id = pytest_project.repository_id
            return SimpleNamespace(
                repository_file_exists=lambda _path: True,
                current_ref_info=lambda: {
                    'branch': 'main',
                    'commit_hash': f'{repository_id:040x}',
                },
            )

        for_product_mock.side_effect = git_service

        result = PytestCaseBatchExecutionService.execute(
            case_ids=[case.id for case in cases],
            test_env=0,
            user_id=self.user.id,
        )

        self.assertEqual(result['repository_count'], 2)
        self.assertEqual(result['execution_group_count'], 2)
        self.assertEqual(
            {group['repository_id'] for group in result['execution_groups']},
            {repository.id for repository in repositories},
        )
