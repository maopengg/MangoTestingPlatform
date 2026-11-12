from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.db.backends.sqlite3.base import DatabaseWrapper
from django.test import SimpleTestCase

from src.apps.test_center.models import ExecutionResult
from src.apps.test_center.services.results.execution_result import ExecutionResultService
from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService


class ExecutionResultPermissionTests(SimpleTestCase):
    @staticmethod
    def compile_query(queryset):
        connection = DatabaseWrapper({'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'},
                                     alias='permission_sql')
        return queryset.query.get_compiler(connection=connection).as_sql()

    def setUp(self):
        self.user = SimpleNamespace(id=1)
        for owner, method, value in [
            (PermissionMenuService, 'is_effective_super_admin', False),
            (ProjectProductScopeService, 'can_view_all_project_data', False),
            (ProjectProductScopeService, 'project_product_ids_for_user', {101}),
        ]:
            mock = patch.object(owner, method, return_value=value)
            mock.start()
            self.addCleanup(mock.stop)

    def test_no_operation_permission_returns_no_results(self):
        with patch.object(PermissionMenuService, 'permission_keys_for_user', return_value={'index.home'}):
            self.assertFalse(ExecutionResultService.visible_results(self.user).exists())
        self.assertFalse(ExecutionResultService.visible_results(None).exists())

    def test_asset_results_require_their_own_permission_and_product_scope(self):
        for permission, target in [('api.case:read', 'api_case'), ('ui.case:change', 'ui_case'),
                                   ('pytest.case:change', 'pytest_case')]:
            with self.subTest(permission=permission), patch.object(
                    PermissionMenuService, 'permission_keys_for_user', return_value={permission}):
                sql, params = self.compile_query(ExecutionResultService.visible_results(self.user))
                self.assertIn(target, params)
                self.assertIn(101, params)
                self.assertIn('project_product_id', sql)
                self.assertNotIn('api_info', params)

    def test_report_access_uses_report_detail_product_scope(self):
        with patch.object(PermissionMenuService, 'permission_keys_for_user', return_value={'report:read'}):
            sql, params = self.compile_query(ExecutionResultService.visible_results(self.user))
        self.assertIn('test_suite_details', sql)
        self.assertIn('project_product_id', sql)
        self.assertIn(101, params)

    def test_super_admin_can_query_all_results(self):
        with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=True):
            queryset = ExecutionResultService.visible_results(self.user)
        self.assertEqual(queryset.model, ExecutionResult)
        self.assertFalse(queryset.query.where.children)

    def test_result_management_read_matches_global_admin_list_scope(self):
        with patch.object(PermissionMenuService, 'permission_keys_for_user',
                          return_value={'system.execution_result:read'}):
            queryset = ExecutionResultService.visible_results(self.user)
        self.assertEqual(queryset.model, ExecutionResult)
        self.assertFalse(queryset.query.where.children)

    def test_result_management_remove_alone_does_not_grant_content_read(self):
        with patch.object(PermissionMenuService, 'permission_keys_for_user',
                          return_value={'system.execution_result:remove'}):
            self.assertFalse(ExecutionResultService.visible_results(self.user).exists())

    def test_detail_and_file_lookup_keep_the_authorized_queryset(self):
        queryset = MagicMock()
        queryset.filter.return_value.select_related.return_value.defer.return_value.first.return_value = None
        queryset.filter.return_value.select_related.return_value.only.return_value.first.return_value = None
        self.assertIsNone(ExecutionResultService.result_detail(123, queryset=queryset))
        self.assertEqual(ExecutionResultService.open_result_file(123, queryset=queryset), (None, None))
        self.assertEqual(queryset.filter.call_count, 2)
        queryset.filter.assert_called_with(id=123)
