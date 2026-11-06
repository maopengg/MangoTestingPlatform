import re
from types import SimpleNamespace
from unittest.mock import patch

from django.http import QueryDict
from django.test import SimpleTestCase
from django.urls import URLResolver, get_resolver, resolve
from rest_framework.test import APIRequestFactory

from src.apps.user.enums.permission import PageOperationEnum
from src.apps.user.middleware.permission import MenuActionPermission
from src.apps.user.services.http_permission_boundaries import HTTP_PERMISSION_BOUNDARIES
from src.apps.user.services.http_permission_catalog import http_permission_catalog
from src.apps.user.services.http_permission_registry import HTTP_PERMISSION_RULES, permission_for_view
from src.apps.user.services.mcp_permission_registry import MCP_PERMISSION_RULES
from src.apps.user.services.permission import PermissionMenuService
from src.interfaces.mcp.authentication import MangoAuthorizationMiddleware, permission_error


class CrudPermissionCatalogTests(SimpleTestCase):
    def test_user_name_options_are_shared_read_without_user_management_access(self):
        path = '/api/user/info/name'
        match = resolve(path)
        view = match.func.cls()
        view.action = match.func.actions['get']
        self.assertEqual(permission_for_view(view, view.action, 'get'), 'index.home:read')
        metadata = next(row for row in http_permission_catalog()
                        if row['method'] == 'GET' and re.fullmatch(row['pattern'], '/user/info/name'))
        self.assertEqual(metadata['permissions'], ['index.home:read'])
        users = resolve('/api/user/info').func.cls()
        for grants, allowed in (({'index.home:read', 'ui.page:read'}, True),
                                (PermissionMenuService.guest_permission_keys(), True),
                                (set(), False)):
            with self.subTest(grants=grants), \
                    patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False), \
                    patch.object(PermissionMenuService, 'permission_keys_for_user', return_value=grants):
                request = SimpleNamespace(method='GET', path=path, data={}, query_params=QueryDict(),
                                          user=SimpleNamespace(user_obj=SimpleNamespace(id=7)))
                self.assertEqual(MenuActionPermission().has_permission(request, view), allowed)
                request.path = '/api/user/info'
                self.assertFalse(MenuActionPermission().has_permission(request, users))
                for method in ('POST', 'PUT', 'DELETE'):
                    request.method = method
                    self.assertFalse(MenuActionPermission().has_permission(request, users))
        anonymous = SimpleNamespace(method='GET', path=path, data={}, query_params=QueryDict(), user=None)
        self.assertFalse(MenuActionPermission().has_permission(anonymous, view))

    def test_legacy_schema_views_remain_disabled_with_optional_coreapi(self):
        from src.apps.user.enums.permission import HttpPermissionBoundaryEnum

        key = ('rest_framework.schemas.views.SchemaView', 'get', 'get')
        self.assertEqual(HTTP_PERMISSION_BOUNDARIES[key], HttpPermissionBoundaryEnum.DISABLED)
        view = type('SchemaView', (), {'__module__': key[0].rsplit('.', 1)[0]})()
        for user in (None, SimpleNamespace(id=1)):
            request = SimpleNamespace(method='GET', user=SimpleNamespace(user_obj=user))
            self.assertFalse(MenuActionPermission().has_permission(request, view))

    def test_readonly_helpers_require_their_menu_read_permission(self):
        helpers = (
            ('/api/system/socket/current/actuator/status', 'ui.case:read'),
            ('/api/system/variable/value', 'help.variable:read'),
            ('/api/perf/scenario/executors', 'perf.scenario:read'),
            ('/api/functional-test/plan/requirement-options', 'functional.plan:read'),
        )
        guest_keys = PermissionMenuService.guest_permission_keys()
        for path, required in helpers:
            match = resolve(path)
            action = match.func.actions['get']
            view = match.func.cls()
            view.action = action
            self.assertEqual(permission_for_view(view, action, 'get'), required)
            metadata = next(row for row in http_permission_catalog()
                            if row['method'] == 'GET' and re.fullmatch(row['pattern'], path.removeprefix('/api')))
            self.assertEqual(metadata['permissions'], [required])
            for grants, allowed in (({required}, True), (guest_keys, True),
                                    ({'index.home:read'}, False),
                                    ({required.replace(':read', ':change')}, False)):
                with self.subTest(path=path, grants=grants), \
                        patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False), \
                        patch.object(PermissionMenuService, 'permission_keys_for_user', return_value=grants):
                    request = SimpleNamespace(method='GET', path=path, data={}, query_params=QueryDict(),
                                              user=SimpleNamespace(user_obj=SimpleNamespace(id=7)))
                    self.assertEqual(MenuActionPermission().has_permission(request, view), allowed)
            anonymous = SimpleNamespace(method='GET', path=path, data={}, query_params=QueryDict(), user=None)
            self.assertFalse(MenuActionPermission().has_permission(anonymous, view))

    def test_result_options_share_is_public_without_token_or_role(self):
        from src.apps.test_center.api.views.test_suite_details import TestSuiteDetails, TestSuiteExecutionResultService
        from src.apps.user.enums.permission import HttpPermissionBoundaryEnum

        path = '/api/system/test/suite/details/result/options/share'
        match = resolve(path)
        key = (f'{match.func.cls.__module__}.{match.func.cls.__name__}', 'get_detail_result_options', 'get')
        self.assertEqual(HTTP_PERMISSION_BOUNDARIES[key], HttpPermissionBoundaryEnum.PUBLIC)
        self.assertNotIn(key, HTTP_PERMISSION_RULES)
        payload = [{'id': 456}]
        for headers in ({}, {'HTTP_AUTHORIZATION': 'invalid-token'}):
            with self.subTest(headers=bool(headers)), \
                    patch.object(TestSuiteDetails.objects, 'filter') as details, \
                    patch.object(TestSuiteExecutionResultService, 'get_payload_options', return_value=payload) as options, \
                    patch.object(PermissionMenuService, 'permission_keys_for_user', side_effect=AssertionError('Public endpoint must not query role permissions')):
                details.return_value.exists.return_value = True
                request = APIRequestFactory().get(path, {'test_suite_detail_id': 123, 'limit': 20}, **headers)
                response = match.func(request)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data['code'], 200)
                self.assertEqual(response.data['data'], payload)
                options.assert_called_once_with(123, '20')

    def test_public_result_options_still_checks_detail_id(self):
        from src.apps.test_center.api.views.test_suite_details import TestSuiteDetails, TestSuiteExecutionResultService

        path = '/api/system/test/suite/details/result/options/share'
        view = resolve(path).func
        for params in ({}, {'test_suite_detail_id': 'invalid'}, {'test_suite_detail_id': 123}):
            with self.subTest(params=params), \
                    patch.object(TestSuiteDetails.objects, 'filter') as details, \
                    patch.object(TestSuiteExecutionResultService, 'get_payload_options') as options:
                details.return_value.exists.return_value = False
                response = view(APIRequestFactory().get(path, params))
                if params:
                    self.assertEqual(response.data['code'], 200)
                    self.assertEqual(response.data['data'], [])
                else:
                    self.assertNotEqual(response.data['code'], 200)
                options.assert_not_called()

    def test_failure_reasons_share_is_public_without_token_or_role(self):
        from src.apps.test_center.api.views.test_suite_details import TestSuiteFailureReasonService, TestSuite
        from src.apps.user.enums.permission import HttpPermissionBoundaryEnum

        path = '/api/system/test/suite/details/failure-reasons/share'
        match = resolve(path)
        key = (f'{match.func.cls.__module__}.{match.func.cls.__name__}', 'get_failure_reasons', 'get')
        self.assertEqual(HTTP_PERMISSION_BOUNDARIES[key], HttpPermissionBoundaryEnum.PUBLIC)
        self.assertNotIn(key, HTTP_PERMISSION_RULES)
        payload = {'items': [], 'total': 0}
        for headers in ({}, {'HTTP_AUTHORIZATION': 'invalid-token'}):
            with self.subTest(headers=bool(headers)), \
                    patch.object(TestSuite.objects, 'filter') as suites, \
                    patch.object(TestSuiteFailureReasonService, 'top_failure_reasons', return_value=payload) as reasons, \
                    patch.object(PermissionMenuService, 'permission_keys_for_user', side_effect=AssertionError('Public endpoint must not query role permissions')):
                suites.return_value.exists.return_value = True
                request = APIRequestFactory().get(path, {'test_suite_id': 123}, **headers)
                response = match.func(request)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data['code'], 200)
                self.assertEqual(response.data['data'], payload)
                reasons.assert_called_once_with(123)

    def test_public_failure_reasons_still_validates_report_id(self):
        from src.apps.test_center.api.views.test_suite_details import TestSuiteFailureReasonService, TestSuite

        path = '/api/system/test/suite/details/failure-reasons/share'
        view = resolve(path).func
        for params in ({}, {'test_suite_id': 'invalid'}, {'test_suite_id': 123}):
            with self.subTest(params=params), \
                    patch.object(TestSuite.objects, 'filter') as suites, \
                    patch.object(TestSuiteFailureReasonService, 'top_failure_reasons') as reasons:
                suites.return_value.exists.return_value = False
                response = view(APIRequestFactory().get(path, params))
                self.assertNotEqual(response.data['code'], 200)
                reasons.assert_not_called()

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
