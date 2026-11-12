from types import SimpleNamespace
from unittest.mock import patch

from django.http import QueryDict
from django.test import SimpleTestCase
from django.urls import resolve

from src.apps.user.middleware.permission import MenuActionPermission
from src.apps.user.services.authorization.endpoint_permission import EndpointPermissionService
from src.apps.user.services.authorization.http_permission_registry import permission_for_view
from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService
from src.interfaces.mcp.authentication import component_policy, permission_error


class GuestTestingPermissionsTests(SimpleTestCase):
    def setUp(self):
        self.user = SimpleNamespace(id=7, role_id=3, role=SimpleNamespace(name='游客'))
        self.admin_patch = patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False)
        self.admin_patch.start()
        self.addCleanup(self.admin_patch.stop)

    def http_permission(self, path, method):
        match = resolve(path)
        view = match.func.cls()
        view.action = getattr(match.func, 'actions', {}).get(method.lower(), method.lower())
        request = SimpleNamespace(method=method, path=path, data={}, query_params=QueryDict(),
                                  user=SimpleNamespace(user_obj=self.user))
        return MenuActionPermission().has_permission(request, view), view

    def test_guest_http_helpers_use_read_permission_without_stored_role_grants(self):
        helpers = (
            ('/api/system/test/object/test', 'POST', 'config.test_object:read'),
            ('/api/system/variable/value', 'GET', 'help.variable:read'),
            ('/api/ui/element/check', 'POST', 'ui.page:read'),
        )
        with patch.object(EndpointPermissionService, 'for_role', side_effect=AssertionError('游客不读取角色授权')):
            for path, method, expected in helpers:
                with self.subTest(path=path):
                    allowed, view = self.http_permission(path, method)
                    self.assertTrue(allowed)
                    self.assertEqual(permission_for_view(view, view.action, method), expected)

    def test_guest_mcp_helpers_match_http_classification_and_enforce_product_scope(self):
        self.assertEqual(component_policy('evaluate_test_data_expression').permission_key, 'help.variable:read')
        self.assertEqual(component_policy('test_ui_element').permission_key, 'ui.page:read')
        self.assertIsNone(permission_error(self.user, 'evaluate_test_data_expression', {'expression': 'example()'}))
        arguments = {'element_payload': {'element_id': 1}}
        with patch('src.interfaces.mcp.authentication.resolve_project_product_ids', return_value={9}), \
                patch.object(ProjectProductScopeService, 'has_project_product', return_value=True) as scope:
            self.assertIsNone(permission_error(self.user, 'test_ui_element', arguments))
            scope.return_value = False
            self.assertEqual(permission_error(self.user, 'test_ui_element', arguments)['error_code'],
                             'MCP_PROJECT_SCOPE_DENIED')
        with patch('src.interfaces.mcp.authentication.resolve_project_product_ids', return_value=set()):
            self.assertEqual(permission_error(self.user, 'test_ui_element', arguments)['error_code'],
                             'MCP_PROJECT_SCOPE_UNRESOLVED')

    def test_guest_cannot_mutate_assets_or_apply_element_test_results(self):
        for path in ('/api/system/test/object', '/api/ui/element'):
            for method in ('POST', 'PUT', 'DELETE'):
                with self.subTest(path=path, method=method):
                    self.assertFalse(self.http_permission(path, method)[0])
        self.assertFalse(self.http_permission('/api/ui/element/check-result/apply', 'PUT')[0])
        for name in ('create_ui_element', 'update_ui_element', 'delete_ui_element'):
            with self.subTest(tool=name):
                error = permission_error(self.user, name, {'element_id': 1})
                self.assertEqual(error['error_code'], 'MCP_PERMISSION_DENIED')

    def test_anonymous_cannot_use_authenticated_testing_helpers(self):
        match = resolve('/api/system/test/object/test')
        view = match.func.cls()
        view.action = 'test_connection'
        self.assertFalse(MenuActionPermission().has_permission(SimpleNamespace(method='POST', user=None), view))
