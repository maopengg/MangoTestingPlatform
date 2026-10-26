import io
import tempfile
import zipfile
from datetime import datetime, timezone as datetime_timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from mangotools.git.models import GitBranchInfo, GitProviderConfig

from src.apps.auto_pytest.api.serializers.pytest_repository import PytestRepositorySerializer
from src.apps.auto_pytest.api.views.pytest_case import PytestCaseViews
from src.apps.auto_pytest.api.views.pytest_product import PytestProductViews
from src.apps.auto_pytest.api.views.pytest_repository import _default_api_base_url, _validate_repository_provider
from src.apps.auto_pytest.exceptions import AutoPytestError
from src.apps.auto_pytest.models import PytestRepository
from src.apps.auto_pytest.services.base.method_nodes import PytestMethodNodeService
from src.apps.auto_pytest.services.file_management import PytestFileManagementService
from src.apps.auto_pytest.services.git_credentials import PytestGitCredentialService
from src.apps.auto_pytest.services.git_management.repository_service import RepositoryGitService
from src.apps.auto_pytest.services.product_sync import PytestProductSyncService
from src.apps.auto_pytest.services.test_case.ai_inference import PytestCaseAiInferenceService
from src.apps.auto_pytest.services.test_case.batch_update import PytestCaseBatchUpdateService
from src.apps.auto_pytest.services.test_case.directory_tree import PytestCaseDirectoryTreeService
from src.apps.auto_pytest.services.test_case.module_binding import PytestCaseModuleBindingService
from src.apps.auto_pytest.services.test_case.sync import PytestCaseSyncService
from src.apps.auto_pytest.services.test_case.test_case import TestCase as PytestDispatchService
from src.apps.auto_pytest.services.test_report_writing import PtestTestReportWriting
from src.apps.system.enums import ExecutorTaskTypeEnum
from src.apps.task_center.services.execution.executor_task import ExecutorTaskService
from src.apps.test_center.api.views.project import ProjectViews


class PytestCaseRuntimeAuditTests(SimpleTestCase):

    def test_repository_api_address_is_inferred_from_repository_url(self):
        self.assertEqual(
            _default_api_base_url('https://git.example.com:8443/group/repository.git', 'gitlab'),
            'https://git.example.com:8443',
        )
        self.assertEqual(
            _default_api_base_url('git@git.example.com:group/repository.git', 'gitlab'),
            'https://git.example.com',
        )
        self.assertEqual(
            _default_api_base_url('https://github.com/example/repository.git', 'github'),
            'https://api.github.com',
        )

    def test_repository_platform_rejects_known_host_mismatch(self):
        with self.assertRaises(AutoPytestError):
            _validate_repository_provider('https://gitee.com/example/repository.git', 'gitlab')
        _validate_repository_provider('https://git.example.com/group/repository.git', 'gitlab')

    def test_public_repository_connection_checks_remote_branch_without_api_token(self):
        repository = SimpleNamespace(
            id=12,
            credential=None,
            provider='gitlab',
            repo_url='https://git.example.com/group/repository.git',
            remote_project='group/repository',
            default_branch='main',
            active_branch='main',
        )
        service = RepositoryGitService(repository)
        client = Mock()
        client.get_branch.return_value = SimpleNamespace(name='main', commit_hash='abc123')
        all_branches = [
            GitBranchInfo(name='main', commit_hash='abc123', default=True),
            GitBranchInfo(name='feature/demo', commit_hash='def456'),
        ]
        client.list_branches.side_effect = lambda project, keyword=None: (
            all_branches if not keyword else [item for item in all_branches if keyword.lower() in item.name.lower()]
        )
        with patch.object(service, 'api_client', return_value=client):
            result = service.test_connection()
            branches = service.branches('FEATURE')

        self.assertEqual(result['branch_count'], 2)
        self.assertEqual([item['name'] for item in branches], ['feature/demo'])
        client.get_project.assert_called_once_with(project='group/repository')
        client.get_branch.assert_called_once_with('main', project='group/repository')
        client.list_branches.assert_called_with(project='group/repository', keyword='FEATURE')

    def test_repository_connection_rejects_missing_default_branch(self):
        repository = SimpleNamespace(
            id=12,
            credential=None,
            provider='gitlab',
            repo_url='https://git.example.com/group/repository.git',
            remote_project='group/repository',
            default_branch='master',
            active_branch='master',
        )
        service = RepositoryGitService(repository)
        client = Mock()
        client.get_branch.return_value = SimpleNamespace(name='master', commit_hash=None)
        with patch.object(service, 'api_client', return_value=client):
            with self.assertRaises(AutoPytestError):
                service.test_connection()

    def test_gitee_public_repository_connection_does_not_require_token(self):
        repository = SimpleNamespace(id=12, provider='gitee', default_branch='master',
                                     remote_project='example/repository')
        service = RepositoryGitService(repository)
        client = Mock()
        client.get_branch.return_value = SimpleNamespace(commit_hash='abc123')
        client.list_branches.return_value = [GitBranchInfo(name='master', commit_hash='abc123')]
        with patch.object(service, 'api_client', return_value=client):
            result = service.test_connection()
        self.assertTrue(result['success'])
        client.get_project.assert_called_once_with(project='example/repository')

    def test_repository_sync_time_uses_platform_datetime_format(self):
        repository = PytestRepository(
            name='Example Repository',
            provider='gitlab',
            repo_url='https://example.com/example/repository.git',
            remote_project='example/repository',
            last_sync_time=datetime(2026, 9, 17, 18, 17, 25, 551580, tzinfo=datetime_timezone.utc),
        )

        data = PytestRepositorySerializer(repository).data

        self.assertEqual(data['last_sync_time'], '2026-09-17 18:17:25')

    def test_repository_tree_lists_directories_and_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / 'tests' / 'api').mkdir(parents=True)
            (root / 'tests' / 'api' / 'test_auth.py').write_text('def test_auth(): pass')
            (root / '.git').mkdir()
            (root / '.git' / 'config').write_text('hidden')
            service = RepositoryGitService(SimpleNamespace(id=12))

            with patch.object(service, 'ensure_local_repository'), patch.object(
                    service, 'local_dir', return_value=temp_dir
            ):
                entries = service.list_repository_entries()

        self.assertIn({'path': 'tests', 'type': 'directory'}, entries)
        self.assertIn({'path': 'tests/api', 'type': 'directory'}, entries)
        self.assertIn({'path': 'tests/api/test_auth.py', 'type': 'file'}, entries)
        self.assertFalse(any(item['path'].startswith('.git') for item in entries))

    def test_batch_update_normalizes_supported_changes(self):
        updates = PytestCaseBatchUpdateService.normalize_updates([
            {
                'id': '71',
                'changes': {
                    'module': 27,
                    'scenario_tags': [1, 2],
                    'case_people': 3,
                },
            },
        ])

        self.assertEqual(updates[0]['id'], 71)
        self.assertEqual(updates[0]['changes']['scenario_tags'], [1, 2])

    def test_batch_update_rejects_duplicate_case_or_unsupported_field(self):
        invalid_updates = [
            [
                {'id': 71, 'changes': {'name': 'First'}},
                {'id': 71, 'changes': {'name': 'Second'}},
            ],
            [{'id': 71, 'changes': {'file_path': 'tests/test_changed.py'}}],
        ]

        for updates in invalid_updates:
            with self.subTest(updates=updates), self.assertRaises(AutoPytestError):
                PytestCaseBatchUpdateService.normalize_updates(updates)

    def test_ai_inference_rejects_duplicate_case_ids(self):
        with self.assertRaises(AutoPytestError):
            PytestCaseAiInferenceService.normalize_case_ids([71, 71])

    def test_ai_inference_constrains_values_and_excludes_owner(self):
        product = SimpleNamespace(project_product_id=9)
        case = SimpleNamespace(
            id=71,
            name='原名称',
            module_id=27,
            asset_status=0,
            level=1,
            scenario_layer=0,
            scenario_type=0,
            scenario_tags=['routine_regression'],
            scenario_description='',
            project_product=product,
        )
        module = SimpleNamespace(id=27)

        result = PytestCaseAiInferenceService._normalize_predictions(
            [case],
            {9: [module]},
            {
                'predictions': [{
                    'id': 71,
                    'name': '登录权限校验',
                    'module': 999,
                    'asset_status': 999,
                    'level': 0,
                    'scenario_layer': 0,
                    'scenario_type': 3,
                    'scenario_tags': ['smoke_verification', 'unknown'],
                    'scenario_description': '验证未授权用户无法访问受保护接口',
                    'case_people': 999,
                }],
            },
        )[0]

        self.assertEqual(result['module'], 27)
        self.assertEqual(result['asset_status'], 0)
        self.assertEqual(result['level'], 0)
        self.assertEqual(result['scenario_tags'], ['smoke_verification'])
        self.assertNotIn('case_people', result)

    @patch('src.apps.auto_pytest.services.test_case.module_binding.ProductModule.objects')
    def test_module_binding_updates_scoped_cases(self, module_objects):
        update_values = {}

        class FakeQuerySet(list):
            def filter(self, **kwargs):
                case_ids = set(kwargs['id__in'])
                return FakeQuerySet(item for item in self if item.id in case_ids)

            def select_related(self, *_args):
                return self

            def update(self, **kwargs):
                update_values.update(kwargs)
                return len(self)

        module = SimpleNamespace(
            id=27,
            level=3,
            project_product_id=9,
            name='Auth',
            get_full_path=lambda: 'API/Auth',
        )
        module_objects.select_related.return_value.filter.return_value.first.return_value = module
        cases = FakeQuerySet([
            SimpleNamespace(id=71, project_product=SimpleNamespace(project_product_id=9)),
            SimpleNamespace(id=72, project_product=SimpleNamespace(project_product_id=9)),
        ])

        result = PytestCaseModuleBindingService.bind.__wrapped__(
            PytestCaseModuleBindingService,
            cases,
            [71, 72],
            27,
            3,
        )

        self.assertEqual(result['updated_count'], 2)
        self.assertEqual(result['module']['full_path'], 'API/Auth')
        self.assertEqual(update_values['module_id'], 27)
        self.assertEqual(update_values['update_user_id'], 3)
        self.assertEqual(update_values['file_status'], 1)

    def test_module_binding_rejects_empty_case_ids(self):
        with self.assertRaises(AutoPytestError):
            PytestCaseModuleBindingService.normalize_case_ids([])

    def test_directory_tree_groups_cases_by_repository_and_file_path(self):
        class FakeQuerySet(list):
            def select_related(self, *_args):
                return self

            def order_by(self, *_args):
                return self

        repository = SimpleNamespace(id=11, name='Example Repository')
        pytest_project = SimpleNamespace(
            id=37,
            name='bdd_api',
            file_name='auto_tests/api/bdd_api',
            repository=repository,
            repository_id=repository.id,
            enabled=True,
        )
        cases = FakeQuerySet([
            SimpleNamespace(
                id=76,
                project_product=pytest_project,
                file_path='auto_tests/api/bdd_api/test_cases/websocket/test_websocket.py',
                source_status=0,
                asset_status=0,
            ),
            SimpleNamespace(
                id=77,
                project_product=pytest_project,
                file_path='auto_tests/api/bdd_api/test_cases/orders/test_orders.py',
                source_status=0,
                asset_status=0,
            ),
        ])

        tree = PytestCaseDirectoryTreeService.build(cases)

        self.assertEqual(tree[0]['title'], 'Example Repository')
        self.assertEqual(tree[0]['case_count'], 2)
        self.assertEqual(tree[0]['children'][0]['title'], 'bdd_api')
        self.assertEqual(tree[0]['children'][0]['children'][0]['title'], 'test_cases')
        self.assertEqual(
            [node['title'] for node in tree[0]['children'][0]['children'][0]['children']],
            ['orders', 'websocket'],
        )
        self.assertEqual(
            tree[0]['children'][0]['children'][0]['children'][1]['children'][0]['path'],
            'auto_tests/api/bdd_api/test_cases/websocket/test_websocket.py',
        )
        self.assertEqual(
            tree[0]['children'][0]['children'][0]['children'][1]['children'][0]['case_id'],
            76,
        )
        self.assertEqual(
            tree[0]['children'][0]['children'][0]['children'][1]['children'][0]['source_status'],
            0,
        )

    @patch.object(PytestCaseSyncService, 'resolve_case_feature_path')
    def test_feature_file_path_is_lazily_resolved_for_existing_case(self, resolve_mock):
        resolve_mock.return_value = 'auto_tests/example/login.feature'
        case = SimpleNamespace(id=18, feature_file_path=None)

        path = PytestFileManagementService.case_file_path(case, 'feature')

        self.assertEqual(path, 'auto_tests/example/login.feature')
        resolve_mock.assert_called_once_with(case, persist=True)

    def test_feature_file_is_resolved_from_scenario_constant(self):
        git_service = Mock()
        git_service.repo_file_path.side_effect = RepositoryGitService.repo_file_path
        git_service.remote_file_content.return_value = '''\
from pytest_bdd import scenario
FEATURE = "../../features/websocket/websocket.feature"
@scenario(FEATURE, "连接")
def test_websocket():
    pass
'''

        result = PytestCaseSyncService._find_feature_path(
            'auto_tests/api/bdd_api/test_cases/websocket/test_websocket.py',
            ['auto_tests/api/bdd_api/features/websocket/websocket.feature'],
            git_service,
        )

        self.assertEqual(
            result,
            'auto_tests/api/bdd_api/features/websocket/websocket.feature',
        )

    def test_feature_file_falls_back_to_test_prefix_name(self):
        git_service = Mock()
        git_service.repo_file_path.side_effect = RepositoryGitService.repo_file_path
        git_service.remote_file_content.return_value = 'def test_login(): pass'
        result = PytestCaseSyncService._find_feature_path(
            'auto_tests/ui/project/test_cases/login/test_login.py',
            ['auto_tests/ui/project/features/login.feature'],
            git_service,
        )

        self.assertEqual(
            result,
            'auto_tests/ui/project/features/login.feature',
        )

    @patch('src.apps.auto_pytest.services.test_report_writing.ExecutionResultService.save_result')
    @patch('src.apps.auto_pytest.services.test_report_writing.PytestCase.objects.get')
    def test_case_result_does_not_touch_content_update_time(self, get_mock, save_result_mock):
        case = SimpleNamespace(id=18, status=None, save=Mock())
        get_mock.return_value = case
        result = SimpleNamespace(
            dispatch_id='pytest-dispatch-18',
            source_snapshot={'commit_hash': 'abc123'},
            id=18,
            name='test_contract',
            status=1,
            result_data={'passed': True},
        )

        PtestTestReportWriting.update_pytest_test_case.__wrapped__(PtestTestReportWriting, result)

        case.save.assert_called_once_with(update_fields=['status'])
        self.assertEqual(
            save_result_mock.call_args.kwargs['source_snapshot'],
            {'commit_hash': 'abc123'},
        )
        self.assertEqual(save_result_mock.call_args.kwargs['task_id'], 'pytest-dispatch-18')


@override_settings(CACHES={
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'pytest-git-credentials-tests',
    },
})
class PytestGitCredentialServiceTests(SimpleTestCase):
    def tearDown(self):
        cache.clear()

    @patch('src.apps.auto_pytest.services.git_credentials.RepositoryGitService.provider_config')
    def test_credential_reference_is_bound_to_executor(self, provider_config_mock):
        provider_config_mock.return_value = SimpleNamespace(access_token='secret-token')

        repository = SimpleNamespace(id=12, credential=None)
        reference = PytestGitCredentialService.issue(
            'executor-a',
            repository=repository,
            dispatch_id='dispatch-a',
        )

        self.assertNotEqual(reference, 'secret-token')
        self.assertEqual(
            PytestGitCredentialService.resolve(
                reference,
                'executor-a',
                repository_id=12,
                dispatch_id='dispatch-a',
            ),
            {'access_token': 'secret-token', 'username': None, 'password': None},
        )
        with self.assertRaises(AutoPytestError):
            PytestGitCredentialService.resolve(
                reference,
                'executor-a',
                repository_id=12,
                dispatch_id='dispatch-a',
            )

    @patch('src.apps.auto_pytest.services.git_credentials.RepositoryGitService.provider_config')
    def test_credential_reference_rejects_wrong_repository_or_dispatch(self, provider_config_mock):
        provider_config_mock.return_value = SimpleNamespace(access_token='secret-token')
        repository = SimpleNamespace(id=12, credential=None)
        reference = PytestGitCredentialService.issue(
            'executor-a',
            repository=repository,
            dispatch_id='dispatch-a',
        )

        with self.assertRaises(AutoPytestError):
            PytestGitCredentialService.resolve(
                reference,
                'executor-a',
                repository_id=13,
                dispatch_id='dispatch-a',
            )
        with self.assertRaises(AutoPytestError):
            PytestGitCredentialService.resolve(
                reference,
                'executor-a',
                repository_id=12,
                dispatch_id='dispatch-b',
            )


class PytestExecutorTaskProjectionTests(SimpleTestCase):
    def test_failed_executor_task_projects_case_failure(self):
        task = SimpleNamespace(
            task_type=ExecutorTaskTypeEnum.PYTEST_EXECUTION.value,
            payload={
                'func_name': 'p_case',
                'func_args': {
                    'id': 18,
                    'name': 'test_contract',
                    'dispatch_id': 'pytest-dispatch-18',
                    'source_snapshot': {'commit_hash': 'abc123'},
                },
            },
        )

        wrapper = PtestTestReportWriting.__dict__['update_pytest_test_case'].__func__
        with patch.object(wrapper, '__wrapped__') as update_mock:
            ExecutorTaskService._project_business_result(
                task,
                {},
                success=False,
                error_message='repository download failed',
            )

        result = update_mock.call_args.args[1]
        self.assertEqual(result.id, 18)
        self.assertEqual(result.status, 0)
        self.assertEqual(result.dispatch_id, 'pytest-dispatch-18')
        self.assertEqual(result.source_snapshot, {'commit_hash': 'abc123'})
        self.assertEqual(
            result.result_data[0]['statusDetails']['message'],
            'repository download failed',
        )


@override_settings(CACHES={
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'pytest-dispatch-security-tests',
    },
})
class PytestDispatchSecurityTests(SimpleTestCase):
    @staticmethod
    def case_object():
        project_product = SimpleNamespace(id=5, name='Example Product')
        repository = SimpleNamespace(id=3, name='Example Repository')
        pytest_project = SimpleNamespace(
            id=7,
            name='Example Pytest Project',
            file_name='auto_tests/example',
            working_directory='auto_tests/example',
            pytest_config_path=None,
            repository=repository,
            repository_id=repository.id,
            project_product=project_product,
        )
        return SimpleNamespace(
            id=18,
            name='test_contract',
            project_product=pytest_project,
            project_product_id=pytest_project.id,
            module=SimpleNamespace(name='Example Module'),
            case_people=SimpleNamespace(name='Tester'),
            file_path='auto_tests/example/test_contract.py',
            file_status=0,
            source_status=0,
            asset_status=0,
            status=2,
            save=Mock(),
        )

    @patch.object(RepositoryGitService, 'for_product')
    @patch('src.apps.auto_pytest.services.test_case.test_case.PytestCase.objects.get')
    def test_dispatch_rejects_case_missing_from_current_branch(
            self,
            get_case_mock,
            for_product_mock,
    ):
        case = self.case_object()
        get_case_mock.return_value = case
        for_product_mock.return_value.repository_file_exists.return_value = False

        with self.assertRaises(AutoPytestError):
            PytestDispatchService('executor-user', is_send=False).test_case(18, 0)

        case.save.assert_not_called()

    @patch.object(RepositoryGitService, 'for_product')
    @patch('src.apps.auto_pytest.services.test_case.test_case.PytestCase.objects.get')
    def test_dispatch_reports_missing_case_owner_as_business_error(
            self,
            get_case_mock,
            for_product_mock,
    ):
        case = self.case_object()
        case.case_people = None
        get_case_mock.return_value = case
        for_product_mock.return_value.repository_file_exists.return_value = True

        with self.assertRaises(AutoPytestError) as error:
            PytestDispatchService('executor-user', is_send=False).test_case(18, 0)

        self.assertEqual(error.exception.msg, 'Pytest Case 未设置用例负责人')
        case.save.assert_not_called()

    @patch.object(RepositoryGitService, 'for_product')
    @patch('src.apps.auto_pytest.services.test_case.test_case.PytestGitCredentialService.issue',
           return_value='credential-reference')
    @patch('src.apps.auto_pytest.services.test_case.test_case.PytestCase.objects.get')
    def test_dispatch_payload_contains_reference_not_access_token(
            self,
            get_case_mock,
            _issue_mock,
            for_product_mock,
    ):
        case = self.case_object()
        get_case_mock.return_value = case
        git_service = for_product_mock.return_value
        git_service.repository_file_exists.return_value = True
        git_service.current_ref_info.return_value = {'branch': 'main', 'commit_hash': 'abc123'}
        git_service.repo_url.return_value = 'https://example.com/example/repository.git'
        git_service.provider_config.return_value = SimpleNamespace(
            provider='gitlab',
            base_url='https://example.com',
            default_project='example/repository',
            access_token='must-not-be-persisted',
        )

        payload = PytestDispatchService('executor-user', is_send=False).test_case(18, 0)

        self.assertIsNone(payload['git_access_token'])
        self.assertEqual(payload['git_credential_ref'], 'credential-reference')
        public_payload = PytestDispatchService.public_dispatch_data(payload)
        self.assertNotIn('git_access_token', public_payload)
        self.assertNotIn('git_credential_ref', public_payload)
        case.save.assert_called_once_with(update_fields=['status'])

    @patch.object(RepositoryGitService, 'for_product')
    @patch('src.apps.auto_pytest.services.test_case.test_case.PytestGitCredentialService.issue',
           return_value='credential-reference')
    @patch('src.apps.auto_pytest.services.test_case.test_case.PytestCase.objects.get')
    def test_dispatch_allows_case_without_module(
            self,
            get_case_mock,
            _issue_mock,
            for_product_mock,
    ):
        case = self.case_object()
        case.module = None
        get_case_mock.return_value = case
        git_service = for_product_mock.return_value
        git_service.repository_file_exists.return_value = True
        git_service.current_ref_info.return_value = {'branch': 'main', 'commit_hash': 'abc123'}
        git_service.repo_url.return_value = 'https://example.com/example/repository.git'
        git_service.provider_config.return_value = SimpleNamespace(
            provider='gitlab',
            base_url='https://example.com',
            default_project='example/repository',
        )

        payload = PytestDispatchService('executor-user', is_send=False).test_case(18, 0)

        self.assertIsNone(payload['module_name'])
        case.save.assert_called_once_with(update_fields=['status'])

    @patch.object(RepositoryGitService, 'for_product')
    @patch('src.apps.auto_pytest.services.test_case.test_case.PytestGitCredentialService.issue',
           return_value='credential-reference')
    @patch('src.apps.auto_pytest.services.test_case.test_case.PytestCase.objects.get')
    def test_dispatch_failure_does_not_mark_case_running(
            self,
            get_case_mock,
            _issue_mock,
            for_product_mock,
    ):
        case = self.case_object()
        get_case_mock.return_value = case
        git_service = for_product_mock.return_value
        git_service.repository_file_exists.return_value = True
        git_service.current_ref_info.return_value = {'branch': 'main', 'commit_hash': 'abc123'}
        git_service.repo_url.return_value = 'https://example.com/example/repository.git'
        git_service.provider_config.return_value = SimpleNamespace(
            provider='gitlab',
            base_url='https://example.com',
            default_project='example/repository',
            access_token='must-not-be-persisted',
        )
        service = PytestDispatchService('executor-user')

        with patch.object(
                PytestDispatchService,
                '_TestCase__socket_send',
                side_effect=RuntimeError('dispatch failed'),
        ):
            with self.assertRaises(RuntimeError):
                service.test_case(18, 0)

        case.save.assert_not_called()


class PytestProjectScopeTests(SimpleTestCase):
    @patch.object(PytestProductSyncService, 'active_project_ids', return_value=[])
    @patch.object(ProjectViews, '_allowed_project_queryset')
    @patch.object(ProjectViews, '_allowed_product_queryset')
    def test_project_pytest_options_resolve_active_paths_in_own_action(
            self,
            product_queryset_mock,
            project_queryset_mock,
            active_ids_mock,
    ):
        project_queryset_mock.return_value.values_list.return_value = []
        request = SimpleNamespace(user={}, query_params={})

        response = ProjectViews().project_pytest_name(request)

        self.assertEqual(response.data['data'], [])
        active_ids_mock.assert_called_once_with()
        product_queryset_mock.assert_called_once_with(request)

    @patch('src.apps.auto_pytest.api.views.pytest_case.ProjectProductScopeService.has_project_product',
           return_value=False)
    @patch('src.apps.auto_pytest.api.views.pytest_case.PermissionMenuService.is_effective_super_admin',
           return_value=False)
    @patch('src.apps.auto_pytest.api.views.pytest_case.PytestCase.objects.filter')
    def test_case_scope_rejects_out_of_scope_case(
            self,
            filter_mock,
            _super_admin_mock,
            _scope_mock,
    ):
        filter_mock.return_value.values_list.return_value.first.return_value = 5
        request = SimpleNamespace(user=SimpleNamespace(user_obj=SimpleNamespace(id=7)))

        self.assertFalse(PytestCaseViews._has_case_scope(request, 18))

    @patch('src.apps.auto_pytest.api.views.pytest_product.ProjectProductScopeService.has_project_product',
           return_value=False)
    @patch('src.apps.auto_pytest.api.views.pytest_product.PermissionMenuService.is_effective_super_admin',
           return_value=False)
    @patch('src.apps.auto_pytest.api.views.pytest_product.PytestProduct.objects.filter')
    def test_product_scope_rejects_out_of_scope_product(
            self,
            filter_mock,
            _super_admin_mock,
            _scope_mock,
    ):
        filter_mock.return_value.values_list.return_value.first.return_value = 5
        request = SimpleNamespace(user=SimpleNamespace(user_obj=SimpleNamespace(id=7)))

        self.assertFalse(PytestProductViews._has_product_scope(request, 11))


class PytestGitManagementSafetyTests(SimpleTestCase):
    @staticmethod
    def _api_repository():
        return SimpleNamespace(
            id=37,
            name='Example Repository',
            credential=None,
            provider='gitlab',
            repo_url='https://git.example.com/example/repository.git',
            api_base_url='https://git.example.com',
            remote_project='example/repository',
            default_branch='main',
            active_branch='main',
            current_commit=None,
        )

    @staticmethod
    def _archive(content='def test_example():\n    assert True\n'):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w') as zipped:
            zipped.writestr('repository-abc/tests/test_example.py', content)
        return archive.getvalue()

    def test_api_snapshot_is_used_for_preview_and_staged_edits(self):
        repository = self._api_repository()
        service = RepositoryGitService(repository)
        client = Mock()
        client.get_branch.return_value = GitBranchInfo(name='main', commit_hash='abc123')
        client.download_archive.return_value = self._archive()

        with tempfile.TemporaryDirectory() as directory, override_settings(GIT_WORKSPACE_DIR=directory), patch.object(
                service, 'api_client', return_value=client,
        ), patch.object(service, '_persist_ref'):
            entries = service.list_repository_entries()
            self.assertIn({'path': 'tests/test_example.py', 'type': 'file'}, entries)
            self.assertFalse(service.local_info()['is_dirty'])
            service.write_local_file('tests/test_example.py', 'def test_example():\n    assert False\n')
            self.assertTrue(service.local_info()['is_dirty'])
            with self.assertRaises(AutoPytestError):
                service.pull()

        client.download_archive.assert_called_once_with('abc123', project='example/repository')

    def test_api_push_updates_staged_file_without_git_command(self):
        repository = self._api_repository()
        service = RepositoryGitService(repository)
        client = Mock()
        remote_head = {'value': 'abc123'}
        client.get_branch.side_effect = lambda *_args, **_kwargs: GitBranchInfo(
            name='main', commit_hash=remote_head['value'],
        )
        client.download_archive.return_value = self._archive()
        client.upsert_file.side_effect = lambda *_args, **_kwargs: remote_head.update(value='def456')
        config = GitProviderConfig(
            provider='gitlab', base_url='https://git.example.com',
            access_token='placeholder', default_project='example/repository',
        )

        with tempfile.TemporaryDirectory() as directory, override_settings(GIT_WORKSPACE_DIR=directory), patch.object(
                service, 'api_client', return_value=client,
        ), patch.object(service, 'provider_config', return_value=config), patch.object(service, '_persist_ref'):
            service.write_local_file('tests/test_example.py', 'def test_example():\n    assert False\n')
            result = service.commit_and_push_current_branch('Update example')

        self.assertFalse(result['is_dirty'])
        self.assertEqual(result['full_commit_hash'], 'def456')
        client.upsert_file.assert_called_once_with(
            'tests/test_example.py', 'def test_example():\n    assert False\n',
            'main', 'Update example', project='example/repository',
        )

    def test_source_change_refreshes_snapshot_even_when_branch_and_commit_are_unchanged(self):
        repository = self._api_repository()
        service = RepositoryGitService(repository)
        client = Mock()
        client.get_branch.return_value = GitBranchInfo(name='main', commit_hash='same-commit')
        client.download_archive.side_effect = [self._archive('old source'), self._archive('new source')]
        with tempfile.TemporaryDirectory() as directory, override_settings(GIT_WORKSPACE_DIR=directory), patch.object(
                service, 'api_client', return_value=client,
        ):
            service.ensure_local_repository()
            repository.remote_project = 'example/new-repository'
            self.assertEqual(service.remote_file_content('tests/test_example.py'), 'new source')
        self.assertEqual(client.download_archive.call_count, 2)
        client.download_archive.assert_called_with('same-commit', project='example/new-repository')

    def test_source_change_preserves_unpushed_local_edits(self):
        repository = self._api_repository()
        service = RepositoryGitService(repository)
        client = Mock()
        client.get_branch.return_value = GitBranchInfo(name='main', commit_hash='same-commit')
        client.download_archive.return_value = self._archive('original')
        with tempfile.TemporaryDirectory() as directory, override_settings(GIT_WORKSPACE_DIR=directory), patch.object(
                service, 'api_client', return_value=client,
        ), patch.object(service, '_persist_ref'):
            service.write_local_file('tests/test_example.py', 'local edits')
            with self.assertRaises(AutoPytestError):
                service.validate_source_change()
            repository.remote_project = 'example/new-repository'
            with self.assertRaises(AutoPytestError):
                service.ensure_local_repository()
            self.assertEqual((Path(service.local_dir()) / 'tests/test_example.py').read_text(), 'local edits')
        client.download_archive.assert_called_once()

    def test_legacy_snapshot_with_local_edits_is_still_usable_without_source_change(self):
        repository = self._api_repository()
        service = RepositoryGitService(repository)
        client = Mock()
        client.get_branch.return_value = GitBranchInfo(name='main', commit_hash='same-commit')
        client.download_archive.return_value = self._archive('original')
        with tempfile.TemporaryDirectory() as directory, override_settings(GIT_WORKSPACE_DIR=directory), patch.object(
                service, 'api_client', return_value=client,
        ), patch.object(service, '_persist_ref'):
            service.write_local_file('tests/test_example.py', 'local edits')
            state = service._read_state()
            state.pop('source')
            service._write_state(state)
            repository.current_commit = 'same-commit'
            self.assertEqual(service.remote_file_content('tests/test_example.py'), 'local edits')
            self.assertEqual(service._read_state()['source'], service.source_identity())
        client.download_archive.assert_called_once()

    def test_api_branch_switch_keeps_selected_branch_after_refresh(self):
        repository = self._api_repository()
        service = RepositoryGitService(repository)
        client = Mock()
        client.get_branch.side_effect = lambda name, **_kwargs: GitBranchInfo(
            name=name, commit_hash='def456' if name == 'feature/demo' else 'abc123',
        )
        client.download_archive.return_value = self._archive()

        def persist_ref(branch, commit_hash):
            repository.active_branch = branch
            repository.current_commit = commit_hash

        with tempfile.TemporaryDirectory() as directory, override_settings(GIT_WORKSPACE_DIR=directory), patch.object(
                service, 'api_client', return_value=client,
        ), patch.object(service, '_persist_ref', side_effect=persist_ref):
            service.ensure_local_repository()
            result = service.switch_branch('feature/demo')
            self.assertEqual(result['active_branch'], 'feature/demo')
            self.assertEqual(result['full_commit_hash'], 'def456')

        self.assertEqual(client.download_archive.call_count, 2)
        client.download_archive.assert_called_with('def456', project='example/repository')

    def test_api_snapshot_rejects_archive_path_traversal(self):
        repository = self._api_repository()
        service = RepositoryGitService(repository)
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w') as zipped:
            zipped.writestr('repository-abc/../../outside.py', 'print("outside")')
        client = Mock()
        client.get_branch.return_value = GitBranchInfo(name='main', commit_hash='abc123')
        client.download_archive.return_value = archive.getvalue()

        with tempfile.TemporaryDirectory() as directory, override_settings(GIT_WORKSPACE_DIR=directory), patch.object(
                service, 'api_client', return_value=client,
        ):
            with self.assertRaises(AutoPytestError):
                service.ensure_local_repository()
            self.assertFalse((Path(directory) / 'pytest' / 'outside.py').exists())

    def test_missing_repository_file_returns_business_error_without_local_path(self):
        service = RepositoryGitService(SimpleNamespace(id=7))

        with patch.object(service, 'ensure_local_repository'), patch.object(
                service,
                '_safe_local_path',
                return_value='/private/runtime/repository/missing.py',
        ), self.assertRaises(AutoPytestError) as error:
            service.remote_file_content('missing.py')

        self.assertIn('当前分支中的文件无法读取', error.exception.msg)
        self.assertNotIn('/private/runtime', error.exception.msg)

    @patch('src.apps.auto_pytest.services.git_management.repository_service.os.path.isfile', return_value=True)
    def test_repository_file_check_restores_persisted_branch_first(self, _isfile_mock):
        service = RepositoryGitService(SimpleNamespace(id=7))

        with patch.object(service, 'ensure_local_repository') as ensure_mock, patch.object(
                service,
                '_safe_local_path',
                return_value='/tmp/repository/test_case.py',
        ):
            self.assertTrue(service.repository_file_exists('test_case.py'))

        ensure_mock.assert_called_once_with()

    def test_repository_paths_are_normalized_and_absolute_paths_are_rejected(self):
        self.assertEqual(
            RepositoryGitService.repo_file_path('tests/./api/test_auth.py'),
            'tests/api/test_auth.py',
        )
        self.assertEqual(RepositoryGitService.repo_file_path('.'), '.')
        for invalid_path in ('../outside.py', '/tmp/outside.py', 'C:/outside.py', 'tests/\x00bad.py'):
            with self.subTest(path=invalid_path), self.assertRaises(AutoPytestError):
                RepositoryGitService.repo_file_path(invalid_path)

    def test_method_nodes_include_source_line_for_editor_actions(self):
        nodes = PytestMethodNodeService._ast_nodes_from_content(
            'def helper():\n'
            '    pass\n\n'
            'def test_contract():\n'
            '    pass\n\n'
            'class TestSocket:\n'
            '    def test_connect(self):\n'
            '        pass\n',
            'auto_tests/api/test_contract.py',
        )

        self.assertEqual(
            [(node['method_name'], node['line_number']) for node in nodes],
            [('test_contract', 4), ('test_connect', 8)],
        )
