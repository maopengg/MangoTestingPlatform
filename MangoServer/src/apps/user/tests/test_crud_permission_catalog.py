from types import SimpleNamespace
from unittest.mock import patch

from django.http import QueryDict
from django.test import SimpleTestCase
from django.urls import URLResolver, get_resolver

from src.apps.user.enums.permission import PageOperationEnum
from src.apps.user.middleware.permission import MenuActionPermission
from src.apps.user.services.http_permission_boundaries import HTTP_PERMISSION_BOUNDARIES
from src.apps.user.services.http_permission_catalog import http_permission_catalog
from src.apps.user.services.http_permission_registry import HTTP_PERMISSION_RULES, permission_for_view
from src.apps.user.services.mcp_permission_registry import MCP_PERMISSION_RULES
from src.apps.user.services.permission import PermissionMenuService
from src.interfaces.mcp.authentication import MangoAuthorizationMiddleware, permission_error


class CrudPermissionCatalogTests(SimpleTestCase):
    def test_every_http_method_has_one_explicit_permission_or_protocol_boundary(self):
        active = set()

        def walk(patterns):
            for pattern in patterns:
                if isinstance(pattern, URLResolver):
                    walk(pattern.url_patterns)
                    continue
                view = getattr(pattern.callback, 'cls', None) or getattr(pattern.callback, 'view_class', None)
                if view is None:
                    continue
                methods = getattr(pattern.callback, 'actions', None) or {
                    method: method for method in view.http_method_names if hasattr(view, method)
                }
                for method, action in methods.items():
                    if method in {'head', 'options'} or method not in view.http_method_names:
                        continue
                    key = (f'{view.__module__}.{view.__name__}', action, method)
                    active.add(key)
                    self.assertTrue(key in HTTP_PERMISSION_RULES or key in HTTP_PERMISSION_BOUNDARIES, key)

        walk(get_resolver().url_patterns)
        self.assertGreater(len(active), 700)
        self.assertFalse(set(HTTP_PERMISSION_RULES) - active)
        valid = PermissionMenuService.all_permission_keys()
        for key, required in HTTP_PERMISSION_RULES.items():
            for permission in [required] if isinstance(required, str) else required:
                self.assertIn(permission, valid, key)
                self.assertIn(permission.rsplit(':', 1)[1], PageOperationEnum.values, key)

    def test_menu_actions_have_only_four_crud_categories(self):
        def walk(items):
            for item in items:
                actions = item.get('actions') or []
                self.assertEqual(len(actions), len({action['permissionKey'] for action in actions}))
                for action in actions:
                    self.assertIn(action['permissionName'], {'新增', '删除', '修改', '查看'})
                    self.assertIn(action['permissionKey'].rsplit(':', 1)[1], PageOperationEnum.values)
                walk(item.get('children') or [])

        walk(PermissionMenuService.permission_tree())

    def test_unregistered_get_or_post_is_denied_instead_of_guessing_from_its_path(self):
        policy = MenuActionPermission()
        user = SimpleNamespace(user_obj=SimpleNamespace(id=7))
        for admin in (False, True):
            for method in ('GET', 'POST', 'PUT', 'PATCH', 'DELETE'):
                with self.subTest(admin=admin, method=method):
                    request = SimpleNamespace(method=method, path='/api/api/case/unknown/run', user=user,
                                              data={}, query_params=QueryDict())
                    with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=admin), \
                            patch.object(PermissionMenuService, 'permission_keys_for_user', return_value={'api.case:change'}):
                        self.assertFalse(policy.has_permission(request, SimpleNamespace(action='run')))

    def test_removing_a_registered_rule_denies_admin_even_at_own_account_shortcut_path(self):
        from src.apps.user.api.views.user import UserCRUD

        request = SimpleNamespace(method='GET', path='/api/user/info', data={}, query_params=QueryDict('id=7'),
                                  user=SimpleNamespace(user_obj=SimpleNamespace(id=7)))
        with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=True):
            self.assertTrue(MenuActionPermission().has_permission(request, UserCRUD()))
            with patch.dict(HTTP_PERMISSION_RULES, {}, clear=True):
                self.assertFalse(MenuActionPermission().has_permission(request, UserCRUD()))

    def test_repository_upsert_cannot_bypass_a_missing_method_mapping(self):
        from src.apps.auto_pytest.api.views.pytest_repository import PytestRepositoryViews

        with patch.dict(HTTP_PERMISSION_RULES, {}, clear=True):
            for data in ({}, {'id': 7}):
                self.assertIsNone(permission_for_view(PytestRepositoryViews, 'save_repository', 'post', data))
        self.assertIsNone(permission_for_view(PytestRepositoryViews, 'save_repository', 'delete', {'id': 7}))

    def test_mcp_missing_policy_is_hidden_and_denied_even_for_admin(self):
        for admin in (False, True):
            with self.subTest(admin=admin), \
                    patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=admin):
                error = permission_error(SimpleNamespace(id=7), 'unregistered_component', {})
                self.assertEqual(error['error_code'], 'MCP_POLICY_MISSING')
                self.assertFalse(MangoAuthorizationMiddleware._visible(
                    SimpleNamespace(claims={'is_super_admin': admin}, scopes=[]), 'unregistered_component',
                ))

    def test_old_action_keys_do_not_expand_into_new_crud_permissions(self):
        old = {f'api.case:{action}' for action in ('edit', 'create', 'delete', 'execute', 'detail', 'publish')}
        self.assertEqual(PermissionMenuService.filter_current_permission_keys(old), set())
        self.assertEqual(PermissionMenuService.filter_current_permission_keys(old | {'api.case:read'}), {'api.case:read'})

    def test_upsert_checks_new_or_existing_record_separately(self):
        from src.apps.auto_pytest.api.views.pytest_repository import PytestRepositoryViews

        view = PytestRepositoryViews()
        self.assertEqual(permission_for_view(view, 'save_repository', 'post', {}), 'pytest.repository:add')
        self.assertEqual(permission_for_view(view, 'save_repository', 'post', {'id': 7}), 'pytest.repository:change')

    def test_mcp_rules_use_registered_crud_actions_and_keep_extra_read_scope_checks(self):
        valid = PermissionMenuService.all_permission_keys()
        for name, rule in MCP_PERMISSION_RULES.items():
            keys = [rule['permission_key'], *rule['additional_permission_keys']]
            for key in filter(None, keys):
                self.assertIn(key, valid, name)
                self.assertIn(key.rsplit(':', 1)[1], PageOperationEnum.values, name)
        callback = MCP_PERMISSION_RULES['get_api_case_callback_results']
        self.assertEqual(callback['additional_permission_keys'], ('api.mock:read',))

    def test_frontend_catalog_excludes_identity_protocols_and_contains_dynamic_record_rule(self):
        items = http_permission_catalog()
        self.assertGreater(len(items), 600)
        self.assertFalse(any('actuator/tasks' in item['pattern'] or 'perf/run-node' in item['pattern'] for item in items))
        self.assertTrue(any(item.get('updatePermissions') == ['pytest.repository:change'] for item in items))
        self.assertTrue(all(item['pattern'].startswith('^/') and item['pattern'].endswith('$') for item in items))
