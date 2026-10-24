import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.http import QueryDict
from django.test import SimpleTestCase
from django.urls import URLResolver, get_resolver

from src.apps.ai.api.views.agent_task import AiAgentTaskViews
from src.apps.auto_api.api.views.api_headers import ApiHeadersCRUD
from src.apps.auto_api.api.views.api_mock import ApiMockConfigCRUD, ApiMockConfigViews
from src.apps.auto_pytest.api.views.pytest_product import PytestProductViews
from src.apps.auto_pytest.api.views.pytest_repository import PytestRepositoryViews
from src.apps.auto_ui.api.views.ui_live_stream import LiveStreamViews
from src.apps.auto_ui.api.views.ui_page_steps import PageStepsViews
from src.apps.functional_test.api.views.case import ManualTestCaseExportViews
from src.apps.gray_config.api.views.repository import GrayRepositoryCRUD
from src.apps.system.api.views.cache_data import CacheDataViews
from src.apps.system.api.views.runtime_center import RuntimeCenterViews
from src.apps.system.services.runtime_center.overview import RuntimeOverviewService
from src.apps.system.services.runtime_center.recent_errors import RecentErrorsService
from src.apps.task_center.api.views.task_group import ScheduledTaskGroupViews
from src.apps.test_center.api.views.data_source import DataSourceCRUD, DataSourceViews
from src.apps.test_center.api.views.execution_result import ExecutionResultViews
from src.apps.user.middleware.permission import MenuActionPermission
from src.apps.user.services.permission import PermissionMenuService
from src.interfaces.mcp.authentication import permission_error


class RolePermissionTests(SimpleTestCase):
    def setUp(self):
        self.user = SimpleNamespace(id=1)
        self.policy = MenuActionPermission()
        self.super_admin = patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False)
        self.super_admin.start()
        self.addCleanup(self.super_admin.stop)

    def request(self, method, path, data=None):
        return SimpleNamespace(method=method.upper(), path=path, data=data or {}, query_params=QueryDict(),
                               user=SimpleNamespace(user_obj=self.user))

    def assert_grants(self, view, action, method, path, permission, data=None):
        request = self.request(method, path, data)
        view.action, view.request = action, request
        self.assertIn(permission, PermissionMenuService.all_permission_keys())
        with patch.object(PermissionMenuService, 'permission_keys_for_user', return_value={permission}):
            self.assertTrue(self.policy.has_permission(request, view))
        with patch.object(PermissionMenuService, 'permission_keys_for_user', return_value={'index.home'}):
            self.assertFalse(self.policy.has_permission(request, view))

    def test_every_page_has_a_unique_key(self):
        nodes = [page for group in PermissionMenuService.permission_tree() for page in group.get('children', [])]
        keys = [page['permissionKey'] for page in nodes]
        self.assertEqual(len(keys), len(set(keys)))
        for page in nodes:
            self.assertTrue(all(action['permissionKey'].startswith(page['permissionKey'] + ':')
                                for action in page.get('actions', [])))

    def test_registered_permissions_grant_previously_blocked_operations(self):
        cases = [
            (DataSourceCRUD(), None, 'get', '/api/system/data-source', 'config.datasource', {}),
            (DataSourceViews(), 'schemas', 'get', '/api/system/data-source/schemas', 'config.product:edit', {}),
            (DataSourceViews(), 'query', 'post', '/api/system/data-source/query', 'config.datasource:debug', {}),
            (ApiMockConfigCRUD(), None, 'post', '/api/api/mock/config', 'api.mock:create', {}),
            (ApiMockConfigViews(), 'change_state', 'put', '/api/api/mock/config/state', 'api.mock:status', {}),
            (ApiMockConfigViews(), 'debug', 'post', '/api/api/mock/config/debug', 'api.mock:debug', {}),
            (LiveStreamViews(), 'create_workspace', 'post', '/api/ui/live-stream/workspace', 'ui.case:debug', {}),
            (PageStepsViews(), 'copy_page_steps', 'post', '/api/ui/page/steps/copy', 'ui.page_steps:copy', {}),
            (PageStepsViews(), 'heal_apply', 'post', '/api/ui/page/steps/healing/apply', 'ui.page_steps:edit', {}),
            (PageStepsViews(), 'heal_rollback', 'post', '/api/ui/page/steps/healing/rollback', 'ui.page_steps:edit',
             {}),
            (PytestProductViews(), 'pytest_import', 'post', '/api/pytest/product/import', 'pytest.product:create', {}),
            (AiAgentTaskViews(), 'functional_case_start', 'post', '/api/ai/agent/functional-case/start',
             'ai.task:execute', {}),
            (AiAgentTaskViews(), 'api_automation_start', 'post', '/api/ai/agent/api-automation/start',
             'ai.task:execute', {}),
            (RuntimeCenterViews(), 'overview', 'get', '/api/system/runtime/overview', 'system.runtime_center', {}),
            (ManualTestCaseExportViews(), None, 'get', '/api/functional-test/case/export', 'functional.case:export',
             {}),
        ]
        for view, action, method, path, key, data in cases:
            with self.subTest(path=path):
                self.assert_grants(view, action, method, path, key, data)

    def test_read_only_settings_cannot_clear_runtime_cache(self):
        request = self.request('post', '/api/system/cache/runtime/clear')
        view = CacheDataViews()
        view.action = 'clear_runtime_cache'
        with patch.object(PermissionMenuService, 'permission_keys_for_user', return_value={'system.settings'}):
            self.assertFalse(self.policy.has_permission(request, view))
        self.assert_grants(view, 'clear_runtime_cache', 'post', request.path, 'system.settings:debug')

    def test_runtime_overview_cannot_bypass_error_page_or_detail_permissions(self):
        overview = {
            'summary': {'recent_error_count': 1},
            'services': [{'service_name': 'core-api', 'status': 'online', 'log_query': 'query',
                          'instances': [{'metadata': {'host_name': 'internal'}}], 'metadata': {'mode': 'dev'}}],
            'queues': {'pending': 1}, 'diagnostics': [{'message': 'diagnostic'}],
            'recent_errors': [{'traceback': 'private trace'}],
        }
        for granted, has_details in [({'system.runtime_center'}, False),
                                     ({'system.runtime_center', 'system.runtime_center:detail'}, True)]:
            with self.subTest(granted=granted), patch.object(
                    RuntimeOverviewService, 'get_overview', return_value=overview), patch.object(
                PermissionMenuService, 'permission_keys_for_user', return_value=granted):
                visible = RuntimeOverviewService.visible_overview(self.user)
                self.assertNotIn('recent_errors', visible)
                self.assertEqual('log_query' in visible['services'][0], has_details)
                self.assertEqual('metadata' in visible['services'][0], has_details)
                self.assertEqual(bool(visible['diagnostics']), has_details)
                self.assertEqual(bool(visible['queues']), has_details)
        self.assertIn('recent_errors', overview)
        self.assertIn('log_query', overview['services'][0])

    def test_error_list_requires_detail_permission_for_trace_and_log_information(self):
        rows = [{'object_id': 1, 'message': 'summary', 'traceback': 'private trace',
                 'log_query': 'query', 'link': '/timing/fire-record/index', 'context': {'private': 'value'}}]
        for granted, expected in [({'system.runtime_center'}, []),
                                  ({'system.error_record'}, [{'object_id': 1, 'message': 'summary'}]),
                                  ({'system.error_record', 'system.error_record:detail'}, rows)]:
            with self.subTest(granted=granted), patch.object(
                    PermissionMenuService, 'permission_keys_for_user', return_value=granted):
                self.assertEqual(RecentErrorsService.visible_rows(rows, self.user), expected)

    def test_runtime_http_responses_apply_field_permissions(self):
        view = RuntimeCenterViews()
        granted = {'system.runtime_center', 'system.error_record'}
        with patch.object(PermissionMenuService, 'permission_keys_for_user', return_value=granted), patch.object(
                RuntimeOverviewService, 'get_overview', return_value={
                    'services': [], 'queues': {'pending': 1}, 'diagnostics': [],
                    'recent_errors': [{'traceback': 'private trace'}],
                }):
            response = view.overview(self.request('get', '/api/system/runtime/overview'))
        self.assertNotIn('recent_errors', response.data['data'])
        self.assertEqual(response.data['data']['queues'], {})
        with patch.object(PermissionMenuService, 'permission_keys_for_user', return_value=granted), patch.object(
                RecentErrorsService, 'paginate_errors', return_value=(
                        [{'object_id': 1, 'message': 'summary', 'traceback': 'private trace', 'log_query': 'query'}], 1,
                )):
            response = view.recent_errors(self.request('get', '/api/system/runtime/recent-errors'))
        self.assertEqual(response.data['data'], [{'object_id': 1, 'message': 'summary'}])

    def test_headers_status_is_independent_from_edit(self):
        self.assert_grants(ApiHeadersCRUD(), None, 'put', '/api/api/headers', 'api.headers:status',
                           {'id': 1, 'status': 1})
        request = self.request('put', '/api/api/headers', {'id': 1, 'status': 1, 'value': 'updated'})
        view = ApiHeadersCRUD()
        view.request = request
        for granted, expected in [({'api.headers:edit'}, False), ({'api.headers:status'}, False),
                                  ({'api.headers:edit', 'api.headers:status'}, True)]:
            with self.subTest(granted=granted), patch.object(
                    PermissionMenuService, 'permission_keys_for_user', return_value=granted):
                self.assertEqual(self.policy.has_permission(request, view), expected)

    def test_repository_create_and_edit_are_distinct(self):
        self.assert_grants(PytestRepositoryViews(), 'save_repository', 'post', '/api/pytest/repository',
                           'pytest.repository:create')
        self.assert_grants(PytestRepositoryViews(), 'save_repository', 'put', '/api/pytest/repository',
                           'pytest.repository:edit', {'id': 1})

    def test_crud_and_task_group_status_toggles_use_status_permission(self):
        self.assert_grants(GrayRepositoryCRUD(), None, 'put', '/api/gray/repository',
                           'gray.repository:status', {'id': 1, 'status': 0})
        self.assert_grants(ScheduledTaskGroupViews(), 'update', 'put', '/api/system/tasks/groups',
                           'timing.tasks:status', {'id': 1, 'status': 0})

    def test_mcp_updates_cannot_bypass_status_permission(self):
        with patch.object(PermissionMenuService, 'permission_keys_for_user', return_value={'api.public:edit'}):
            error = permission_error(self.user, 'update_api_public_variable', {'public_variable_id': 1, 'status': 0})
        self.assertEqual(error['error_code'], 'MCP_PERMISSION_DENIED')
        self.assertEqual(error['details']['permission'], 'api.public:status')

    def test_execution_result_endpoints_require_an_operation_permission(self):
        for action in ('get_list', 'get_detail', 'get_content', 'get_latest'):
            self.assert_grants(ExecutionResultViews(), action, 'get', '/api/system/execution/result/detail',
                               'api.case:detail')

    def test_capacity_has_no_unimplemented_edit_permission(self):
        self.assertEqual(PermissionMenuService.default_actions_for_menu('perf.capacity'), [])
        for unused in ('api.info:copy', 'pytest.product:execute', 'config.test_object:debug',
                       'config.test_object:detail', 'gray.feature:detail', 'gray.repository:detail',
                       'timing.fire_record:detail'):
            self.assertNotIn(unused, PermissionMenuService.all_permission_keys())

    def test_new_ai_generation_permission_is_not_automatically_granted_to_guests(self):
        self.assertNotIn('ai.task:execute', PermissionMenuService.guest_permission_keys())

    def test_old_database_page_permission_is_normalized_without_expanding_other_pages(self):
        self.assertEqual(PermissionMenuService.normalize_legacy_permission_keys(
            ['config.data_source', 'pytest.product', 'system.settings']),
            {'config.datasource', 'pytest.product', 'system.settings'})

    def test_explicit_http_permission_maps_use_registered_keys(self):
        valid = PermissionMenuService.all_permission_keys()

        def inspect(patterns):
            for pattern in patterns:
                if isinstance(pattern, URLResolver):
                    inspect(pattern.url_patterns)
                    continue
                view = getattr(pattern.callback, 'cls', None)
                if view is None:
                    continue
                maps = (getattr(view, 'action_permission_map', {}) or {},
                        getattr(view, 'permission_key_map', {}) or {})
                for mapping in maps:
                    for required in mapping.values():
                        keys = [required] if isinstance(required, str) else required or []
                        for key in keys:
                            self.assertIn(key, valid, f'{view.__name__}: {key}')

        inspect(get_resolver().url_patterns)

    def test_frontend_explicit_permission_keys_are_registered(self):
        frontend = Path(__file__).resolve().parents[5] / 'mango-console' / 'src'
        self.assertTrue(frontend.exists())
        valid = PermissionMenuService.all_permission_keys()
        for file in frontend.rglob('*'):
            if file.suffix not in ('.vue', '.ts'):
                continue
            content = file.read_text()
            expressions = re.findall(r'v-permission="([^"]+)"', content)
            expressions += re.findall(r'\bpermission:\s*(\[[^\]]*\]|\x27[^\x27]*\x27)', content)
            for expression in expressions:
                for key in re.findall(r"'([a-z_][\w.]*(?::[\w-]+)?)'", expression):
                    self.assertIn(key, valid, f'{file.relative_to(frontend)}: {key}')
