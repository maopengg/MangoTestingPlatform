from types import SimpleNamespace
from unittest.mock import patch

from django.http import QueryDict
from django.test import SimpleTestCase

from src.apps.auto_api.api.views.api_case import ApiCaseCRUD, ApiCaseViews
from src.apps.auto_pytest.api.views.pytest_case import PytestCaseViews
from src.apps.auto_ui.api.views.ui_case import UiCaseViews
from src.apps.user.api.views.user import LoginViews
from src.apps.user.middleware.permission import MenuActionPermission
from src.apps.user.services.authorization.permission import PermissionMenuService
from src.apps.user.tests.permission_fixtures import install_legacy_endpoint_snapshot
from src.interfaces.mcp.authentication import permission_error


class GuestExecutionPermissionTests(SimpleTestCase):
    def setUp(self):
        install_legacy_endpoint_snapshot(self)
        self.user = SimpleNamespace(id=7)
        self.grants = PermissionMenuService.guest_permission_keys()
        for name, result in (('is_effective_super_admin', False), ('permission_keys_for_user', self.grants)):
            mocked = patch.object(PermissionMenuService, name, return_value=result)
            mocked.start()
            self.addCleanup(mocked.stop)

    def test_guest_can_execute_single_and_post_batch_but_not_edit_case(self):
        for view_type, action, method in (
            (ApiCaseViews, 'api_test_case', 'GET'),
            (ApiCaseViews, 'api_test_case_batch', 'POST'),
            (ApiCaseViews, 'api_debug_case_step', 'POST'),
            (UiCaseViews, 'ui_test_case_batch', 'POST'),
            (PytestCaseViews, 'pytest_test_case_batch', 'POST'),
        ):
            with self.subTest(action=action):
                view = view_type()
                view.action = action
                request = SimpleNamespace(method=method, path='/api/example', data={}, query_params=QueryDict(),
                                          user=SimpleNamespace(user_obj=self.user))
                self.assertTrue(MenuActionPermission().has_permission(request, view))
        for method in ('POST', 'PUT', 'DELETE'):
            request = SimpleNamespace(method=method, path='/api/api/case', data={'id': 1}, query_params=QueryDict(),
                                      user=SimpleNamespace(user_obj=self.user))
            self.assertFalse(MenuActionPermission().has_permission(request, ApiCaseCRUD()))

    def test_mcp_execution_still_requires_resolved_authorized_product(self):
        tools = ('run_api_case', 'run_api_case_batch', 'run_api_info', 'debug_api_case_step',
                 'run_ui_case', 'run_ui_case_batch', 'run_ui_page_step',
                 'run_pytest_case', 'run_pytest_case_batch', 'trigger_scheduled_task',
                 'preview_trigger_scheduled_task_impact')
        with patch('src.interfaces.mcp.authentication.resolve_project_product_ids') as product_ids, \
                patch('src.interfaces.mcp.authentication.ProjectProductScopeService.has_project_product') as allowed:
            for tool in tools:
                with self.subTest(tool=tool):
                    product_ids.return_value, allowed.return_value = {11}, True
                    self.assertIsNone(permission_error(self.user, tool, {}))
                    allowed.return_value = False
                    self.assertEqual(permission_error(self.user, tool, {})['error_code'], 'MCP_PROJECT_SCOPE_DENIED')
                    product_ids.return_value = set()
                    self.assertEqual(permission_error(self.user, tool, {})['error_code'], 'MCP_PROJECT_SCOPE_UNRESOLVED')
        self.assertIsNotNone(permission_error(self.user, 'update_api_case', {}))
        self.assertIsNotNone(permission_error(self.user, 'publish_api_case_revision', {}))

    def test_self_registration_is_an_explicit_prelogin_boundary(self):
        view = LoginViews()
        view.action = 'register'
        request = SimpleNamespace(method='POST', user=None, data={}, query_params=QueryDict(), path='/api/register')
        self.assertTrue(MenuActionPermission().has_permission(request, view))
