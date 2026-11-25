from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from django.db import connections, transaction
from django.db.backends.sqlite3.base import DatabaseWrapper
from django.http import QueryDict
from django.test import SimpleTestCase
from django.test.utils import CaptureQueriesContext
from django.urls import resolve

from src.apps.user.enums.permission import EndpointPermissionEffectEnum as Effect
from src.apps.user.exceptions import UserError
from src.apps.user.middleware.permission import MenuActionPermission
from src.apps.user.models import Role
from src.apps.user.services.authorization.role_authorization_transfer import RoleAuthorizationTransferService
from src.apps.user.services.authorization.endpoint_catalog import configurable_endpoint_ids, endpoint_catalog, http_endpoint_id, mcp_endpoint_id
from src.apps.user.services.authorization.endpoint_permission import EndpointPermissionService as Endpoint
from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService
from src.interfaces.mcp.authentication import MangoAuthorizationMiddleware, permission_error


class EndpointAuthorizationTests(SimpleTestCase):
    async def test_real_root_and_domain_mcp_discovery_and_calls_respect_override(self):
        from fastmcp import Client
        from fastmcp.exceptions import ToolError
        from fastmcp.server.auth import AccessToken
        from src.interfaces.mcp.server import mcp_asgi_app
        from src.apps.monitoring.services.logging.task_log import MonitoringTaskLogService
        from src.apps.user.selectors.querysets import UserQuerySelector

        name = 'get_monitoring_task_logs'
        for effect in (Effect.ALLOW, Effect.DENY):
            overrides = {mcp_endpoint_id(name): effect}
            access = AccessToken(token='example-key', client_id='example-client', subject='7', scopes=[],
                                 claims={'endpoint_overrides': overrides})
            for domain in (None, 'monitoring'):
                with self.subTest(effect=effect, domain=domain), \
                        patch.object(MangoAuthorizationMiddleware, '_access', new=AsyncMock(return_value=access)), \
                        patch.object(UserQuerySelector, 'user') as query, \
                        patch.object(Endpoint, 'for_user', return_value=overrides), \
                        patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False), \
                        patch.object(PermissionMenuService, 'permission_keys_for_user', return_value=set()), \
                        patch('src.interfaces.mcp.authentication.resolve_project_product_ids', return_value={1}), \
                        patch.object(ProjectProductScopeService, 'has_project_product', return_value=True), \
                        patch.object(ProjectProductScopeService, 'can_view_all_project_data', return_value=False), \
                        patch.object(ProjectProductScopeService, 'project_product_ids_for_user', return_value={1}), \
                        patch.object(MonitoringTaskLogService, 'tail', return_value={'lines': ['example']}) as tail, \
                        patch('src.interfaces.mcp.tools.monitoring.current_user', return_value=self.user), \
                        patch('src.interfaces.mcp.common.require_mcp_user', return_value=None), \
                        patch('src.interfaces.mcp.common.user_from_auth_token', return_value=self.user), \
                        patch('src.interfaces.mcp.common.log_mcp_tool_call_async'):
                    query.return_value.select_related.return_value.get.return_value = self.user
                    async with Client(mcp_asgi_app(domain).fastmcp_server) as client:
                        names = {tool.name for tool in await client.list_tools()}
                        self.assertEqual(name in names, effect == Effect.ALLOW)
                        if effect == Effect.ALLOW:
                            response = await client.call_tool(name, {'monitoring_task_id': 1})
                            self.assertFalse(response.is_error)
                            self.assertTrue(response.data['success'], response.data)
                            tail.assert_called_once()
                        else:
                            with self.assertRaises(ToolError):
                                await client.call_tool(name, {'monitoring_task_id': 1})
                            tail.assert_not_called()

    def setUp(self):
        self.user = SimpleNamespace(id=7)
        self.http_id = http_endpoint_id('src.apps.auto_api.api.views.api_case.ApiCaseCRUD', 'get', 'get')
        self.mcp_id = mcp_endpoint_id('get_api_case_detail_full')

    def http(self, path='/api/api/case', action=None):
        match = resolve(path)
        view = match.func.cls()
        view.action = action or (getattr(match.func, 'actions', {}) or {}).get('get', 'get')
        request = SimpleNamespace(method='GET', path=path, data={}, query_params=QueryDict(),
                                  user=SimpleNamespace(user_obj=self.user))
        return MenuActionPermission().has_permission(request, view)

    def test_catalog_uses_real_routes_and_registered_tool_descriptions(self):
        catalog = {item['id']: item for item in endpoint_catalog()}
        self.assertIn('/api/api/case', catalog[self.http_id]['urls'])
        self.assertFalse(catalog[self.http_id]['fixed'])
        tool = catalog[mcp_endpoint_id('create_monitoring_task')]
        self.assertIn('监控脚本', tool['description'])
        self.assertFalse(tool['fixed'])
        self.assertEqual(len(catalog), len(endpoint_catalog()))
        for row in catalog.values():
            self.assertLessEqual(len(row['id']), 128)

    def test_override_validation_rejects_unknown_fixed_and_invalid_effects(self):
        fixed = http_endpoint_id('src.apps.user.api.views.user.UserViews', 'get_name', 'get')
        for values in (None, [], {self.http_id: 'inherit'}, {fixed: Effect.ALLOW},
                       {'http.unknown': Effect.DENY}, {self.http_id: True}):
            with self.subTest(values=values), self.assertRaises(UserError):
                Endpoint.validate(values)
        self.assertEqual(Endpoint.validate({self.http_id: Effect.ALLOW}), {self.http_id: Effect.ALLOW})

    def test_missing_documentation_does_not_change_permission_configuration(self):
        from src.apps.user.services.authorization import endpoint_catalog as catalog_module
        before = configurable_endpoint_ids()
        with patch.object(catalog_module, '_mcp_component_metadata', return_value={}):
            rows = catalog_module.endpoint_catalog.__wrapped__()
        self.assertEqual(frozenset(row['id'] for row in rows if not row['fixed']), before)

    def test_decorated_http_methods_keep_function_descriptions_without_parameter_tags(self):
        from src.apps.test_center.api.views.index import IndexViews
        self.assertEqual(IndexViews.case_result_week_sum.__name__, 'case_result_week_sum')
        self.assertIn('获取三个类型的总数', IndexViews.case_result_week_sum.__doc__)
        row = next(item for item in endpoint_catalog() if item['id'] == http_endpoint_id(
            'src.apps.test_center.api.views.index.IndexViews', 'case_result_week_sum', 'get'))
        self.assertEqual(row['description'], '获取三个类型的总数')
        self.assertNotIn('@param', row['description'])
        self.assertNotIn('@return', row['description'])

    async def test_business_resources_and_prompts_require_explicit_interface_grants(self):
        from src.interfaces.mcp.server import mcp_asgi_app
        from src.apps.user.services.authorization.mcp_permission_registry import MCP_PERMISSION_RULES

        server = mcp_asgi_app().fastmcp_server
        resources = await server._list_resources()
        templates = await server._list_resource_templates()
        prompts = await server._list_prompts()
        for item in [*resources, *templates, *prompts]:
            rule = MCP_PERMISSION_RULES[item.name]
            if rule['permission_key']:
                self.assertIn(mcp_endpoint_id(item.name), configurable_endpoint_ids())

    def test_http_and_mcp_are_independent_and_super_admin_bypasses_role(self):
        for admin in (False, True):
            for effect in (Effect.DENY, Effect.ALLOW):
                with self.subTest(admin=admin, effect=effect), \
                        patch.object(Endpoint, 'for_user', return_value={self.http_id: effect}), \
                        patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=admin), \
                        patch.object(PermissionMenuService, 'permission_keys_for_user', return_value=set()), \
                        patch('src.apps.user.services.authorization.model_crud_scope.ModelCrudDataScopePolicy.has_request_permission', return_value=True):
                    self.assertEqual(self.http(), admin or effect == Effect.ALLOW)
                    error = permission_error(self.user, 'get_api_case_detail_full', {})
                    self.assertEqual(error is None, admin)

    def test_super_admin_endpoint_decision_ignores_denial_without_reading_role(self):
        for endpoint in (self.http_id, self.mcp_id):
            with self.subTest(endpoint=endpoint), \
                    patch.object(Endpoint, 'for_user', side_effect=AssertionError('不得读取超管角色授权')):
                self.assertTrue(Endpoint.allows(self.user, endpoint, super_admin=True))
                self.assertTrue(Endpoint.decision({endpoint: Effect.DENY}, endpoint, super_admin=True))
        self.assertFalse(Endpoint.decision({}, 'unregistered', super_admin=True))

    def test_super_admin_product_edit_skips_role_and_department_scope(self):
        from src.apps.test_center.api.views.project_product import ProjectProductCRUD
        from src.apps.user.services.authorization.model_crud_scope import ModelCrudDataScopePolicy

        request = SimpleNamespace(method='PUT', path='/api/system/product', data={'id': 17}, query_params=QueryDict(),
                                  user=SimpleNamespace(user_obj=self.user))
        with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=True), \
                patch.object(Endpoint, 'for_user', side_effect=AssertionError('不得读取超管角色授权')), \
                patch.object(ProjectProductScopeService, 'project_product_ids_for_user',
                             side_effect=AssertionError('不得查询超管部门范围')), \
                patch.object(ProjectProductCRUD, 'has_request_data_scope_permission',
                             side_effect=AssertionError('不得限制超管接口数据范围')):
            self.assertTrue(MenuActionPermission().has_permission(request, ProjectProductCRUD()))
            model = ProjectProductCRUD.model
            queryset = model.objects.all()
            self.assertIs(ModelCrudDataScopePolicy.filter_queryset(model, request, queryset, set()), queryset)
            self.assertTrue(ModelCrudDataScopePolicy.has_request_permission(model, request, set()))
            self.assertTrue(ModelCrudDataScopePolicy.has_data_permission(model, request, {'id': 17}, set()))
            self.assertTrue(ModelCrudDataScopePolicy.has_instance_permission(model, request, model(id=17), set()))

    def test_super_admin_mcp_call_and_discovery_ignore_denial_and_scope(self):
        access = SimpleNamespace(claims={'is_super_admin': True,
                                        'endpoint_permissions': {self.mcp_id: Effect.DENY}}, scopes=[])
        with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=True), \
                patch.object(Endpoint, 'for_user', side_effect=AssertionError('不得读取超管角色授权')), \
                patch('src.interfaces.mcp.authentication.resolve_project_product_ids',
                      side_effect=AssertionError('不得限制超管产品范围')):
            self.assertTrue(MangoAuthorizationMiddleware._visible(access, 'get_api_case_detail_full'))
            self.assertIsNone(permission_error(self.user, 'get_api_case_detail_full', {'case_id': 1}))

    def test_http_allow_cannot_bypass_data_scope(self):
        with patch.object(Endpoint, 'for_user', return_value={self.http_id: Effect.ALLOW}), \
                patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False), \
                patch.object(PermissionMenuService, 'permission_keys_for_user', return_value=set()), \
                patch('src.apps.user.services.authorization.model_crud_scope.ModelCrudDataScopePolicy.has_request_permission', return_value=False):
            self.assertFalse(self.http())

    def test_mcp_call_and_discovery_follow_same_effect(self):
        for effect, expected in ((Effect.DENY, False), (Effect.ALLOW, True)):
            overrides = {self.mcp_id: effect}
            access = SimpleNamespace(claims={'endpoint_overrides': overrides}, scopes=[])
            with self.subTest(effect=effect), patch.object(Endpoint, 'for_user', return_value=overrides), \
                    patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False), \
                    patch.object(PermissionMenuService, 'permission_keys_for_user', return_value=set()), \
                    patch('src.interfaces.mcp.authentication.resolve_project_product_ids', return_value={2}), \
                    patch.object(ProjectProductScopeService, 'has_project_product', return_value=True):
                self.assertEqual(MangoAuthorizationMiddleware._visible(access, 'get_api_case_detail_full'), expected)
                self.assertEqual(permission_error(self.user, 'get_api_case_detail_full', {'case_id': 1}) is None, expected)

    def test_pure_mcp_snapshot_never_inherits_old_category_scopes(self):
        access = SimpleNamespace(claims={'endpoint_permissions': {}}, scopes=['api.case:read'])
        for name in ('get_api_case_detail_full', 'get_api_case_resource', 'api_failure_analysis'):
            self.assertFalse(MangoAuthorizationMiddleware._visible(access, name))

    def test_shared_business_endpoints_are_not_mistaken_for_fixed_options(self):
        rows = {row['id']: row for row in endpoint_catalog()}
        for owner, action, method in (
            ('src.apps.auto_ui.api.views.ui_live_stream.LiveStreamViews', 'create_workspace', 'post'),
            ('src.apps.test_center.api.views.execution_result.ExecutionResultViews', 'get_content', 'get'),
            ('src.apps.evaluation.api.views.case.CaseViews', 'retrieve', 'get'),
        ):
            self.assertFalse(rows[http_endpoint_id(owner, action, method)]['fixed'])

    def test_mcp_allow_keeps_project_and_related_resource_checks(self):
        name = 'get_api_case_callback_deliveries'
        with patch.object(Endpoint, 'for_user', return_value={mcp_endpoint_id(name): Effect.ALLOW}), \
                patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False), \
                patch.object(PermissionMenuService, 'permission_keys_for_user', return_value=set()):
            self.assertEqual(permission_error(self.user, name, {})['error_code'], 'MCP_PERMISSION_DENIED')
        with patch.object(Endpoint, 'for_user', return_value={self.mcp_id: Effect.ALLOW}), \
                patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False), \
                patch.object(PermissionMenuService, 'permission_keys_for_user', return_value=set()), \
                patch('src.interfaces.mcp.authentication.resolve_project_product_ids', return_value={2}), \
                patch.object(ProjectProductScopeService, 'has_project_product', return_value=False):
            self.assertEqual(permission_error(self.user, 'get_api_case_detail_full', {'case_id': 1})['error_code'], 'MCP_PROJECT_SCOPE_DENIED')

    def test_fixed_and_unregistered_entries_cannot_be_changed_by_stale_overrides(self):
        fixed = http_endpoint_id('src.apps.user.api.views.user.UserViews', 'get_name', 'get')
        self.assertNotIn(fixed, configurable_endpoint_ids())
        self.assertTrue(Endpoint.decision({fixed: Effect.DENY}, fixed, True))
        with patch.object(Endpoint, 'for_user', return_value={mcp_endpoint_id('missing'): Effect.ALLOW}):
            self.assertEqual(permission_error(self.user, 'missing', {})['error_code'], 'MCP_POLICY_MISSING')
        anonymous = SimpleNamespace(method='GET', user=None)
        self.assertFalse(MenuActionPermission().has_permission(anonymous, SimpleNamespace()))

    def test_guest_never_reads_stored_overrides(self):
        user = SimpleNamespace(id=7, role_id=1, role=SimpleNamespace(name='游客'))
        with patch.object(Endpoint, 'for_role', side_effect=AssertionError('Guest overrides must not be read')):
            self.assertEqual(Endpoint.for_user(user), Endpoint.from_legacy_keys(PermissionMenuService.guest_permission_keys()))

    def test_other_groups_only_display_fixed_rules_and_never_grant_permissions(self):
        from src.apps.user.services.authorization.endpoint_catalog import fixed_endpoint_tree, grouped_endpoint_catalog
        from src.apps.user.enums.permission import FixedEndpointCategoryEnum
        tree = fixed_endpoint_tree()
        self.assertEqual(tree['menuName'], '其他')
        self.assertTrue(tree['displayOnly'])
        self.assertTrue(all(item['displayOnly'] for item in tree['children']))
        groups = {group['menu_key']: group['endpoints'] for group in grouped_endpoint_catalog()}
        fixed_ids = {row['id'] for row in endpoint_catalog() if row['fixed']}
        menu_fixed = [row for row in endpoint_catalog() if row['fixed'] and row['menu_owners']]
        other_ids = fixed_ids - {row['id'] for row in menu_fixed}
        self.assertEqual({row['id'] for row in groups['__fixed__']}, other_ids)
        self.assertNotIn('__fixed__.default_read', groups)
        for row in menu_fixed:
            for owner in row['menu_owners']:
                self.assertIn(row['id'], {item['id'] for item in groups[owner]})
        classified_ids = set()
        for item in tree['children']:
            self.assertNotIn(item['permissionKey'], PermissionMenuService.all_permission_keys())
            self.assertTrue(all(row['fixed'] for row in groups[item['permissionKey']]))
            classified_ids.update(row['id'] for row in groups[item['permissionKey']])
        self.assertEqual(classified_ids, other_ids)
        self.assertFalse(fixed_ids & configurable_endpoint_ids())
        disabled = groups['__fixed__.disabled']
        self.assertTrue(disabled)
        self.assertTrue(all(row['fixed_enabled'] is False for row in disabled))
        self.assertTrue(all(row['fixed_enabled'] is True for row in groups['__fixed__']
                            if row['fixed_category'] != 'disabled'))
        with self.assertRaises(UserError):
            Endpoint.validate({disabled[0]['id']: Effect.ALLOW})

    def test_fixed_asset_options_stay_in_their_own_model_menu(self):
        from src.apps.user.services.authorization.endpoint_catalog import grouped_endpoint_catalog
        groups = {group['menu_key']: group['endpoints'] for group in grouped_endpoint_catalog()}
        cases = (
            ('src.apps.test_center.api.views.project.ProjectViews', 'get_all_items', 'config.project'),
            ('src.apps.test_center.api.views.project_product.ProjectProductViews', 'get_product_name', 'config.product'),
            ('src.apps.test_center.api.views.product_module.ProductModuleViews', 'tree', 'config.product'),
            ('src.apps.test_center.api.views.notice_group.NoticeGroupViews', 'get_name', 'config.project'),
            ('src.apps.task_center.api.views.time_tasks.TimeTasksViews', 'get_time_obj_name', 'timing.strategy'),
        )
        other_ids = {item['id'] for item in groups['__fixed__']}
        for owner, action, menu in cases:
            endpoint_id = http_endpoint_id(owner, action, 'get')
            with self.subTest(action=action, menu=menu):
                row = next(item for item in groups[menu] if item['id'] == endpoint_id)
                self.assertTrue(row['fixed'])
                self.assertTrue(row['fixed_enabled'])
                self.assertNotIn(endpoint_id, other_ids)


class EndpointPersistenceTests(SimpleTestCase):
    def test_role_json_validation_fails_closed_and_generic_crud_cannot_change_it(self):
        from src.apps.user.api.serializers.user import RoleSerializers
        serializer = RoleSerializers(data={'name': '新角色', 'authorization': {'endpoint_permissions': {self.endpoint: Effect.ALLOW}}})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertNotIn('authorization', serializer.validated_data)
        self.assertNotIn('authorization', RoleSerializers(self.role).data)
        Role.objects.filter(pk=self.role.pk).update(authorization={'version': 99})
        with self.assertRaises(UserError):
            Endpoint.for_role(self.role.id)

    def test_export_import_preserves_denials_is_dry_run_by_default_and_idempotent(self):
        with self.db.cursor() as cursor:
            cursor.execute('CREATE TABLE role_menu_permission (id INTEGER PRIMARY KEY, role_id INTEGER, permission_key TEXT, permission_type TEXT)')
            cursor.executemany('INSERT INTO role_menu_permission VALUES (%s, %s, %s, %s)', [
                (1, self.role.id, 'api.case:read', 'action'), (2, self.role.id, self.endpoint, Effect.DENY)])
        with patch('src.apps.user.services.authorization.role_authorization_transfer.connection', self.db):
            backup = RoleAuthorizationTransferService.export_legacy()
        self.assertEqual(Role.objects.get(pk=self.role.pk).authorization, {})
        self.assertEqual(backup['roles'][0]['authorization']['endpoint_permissions'][self.endpoint], Effect.DENY)
        original_atomic = transaction.atomic
        with patch('src.apps.user.services.authorization.role_authorization_transfer.transaction.atomic', side_effect=lambda *args, **kwargs: original_atomic(*args, **{'using': self.alias, **kwargs})):
            self.assertEqual(RoleAuthorizationTransferService.import_backup(backup)['changed'], 0)
            self.assertEqual(Role.objects.get(pk=self.role.pk).authorization, {})
            self.assertEqual(RoleAuthorizationTransferService.import_backup(backup, apply=True)['changed'], 1)
            self.assertEqual(RoleAuthorizationTransferService.import_backup(backup, apply=True)['pending'], 0)
        self.assertEqual(Endpoint.for_role(self.role.id)[self.endpoint], Effect.DENY)

    def test_import_rejects_conflict_identity_mismatch_and_duplicate_ids_without_changes(self):
        from copy import deepcopy
        self.save(['api.case'], {self.endpoint: Effect.DENY})
        before = Role.objects.get(pk=self.role.pk).authorization
        original_atomic = transaction.atomic
        base = {'format': 'mango-role-authorization-v1', 'roles': [{'id': self.role.id, 'name': self.role.name, 'authorization': before}]}
        conflicting = deepcopy(base)
        conflicting['roles'][0]['authorization']['endpoint_permissions'][self.endpoint] = Effect.ALLOW
        wrong_name = deepcopy(base)
        wrong_name['roles'][0]['name'] = '其他角色'
        duplicate = deepcopy(base)
        duplicate['roles'] *= 2
        with patch('src.apps.user.services.authorization.role_authorization_transfer.transaction.atomic', side_effect=lambda *args, **kwargs: original_atomic(*args, **{'using': self.alias, **kwargs})):
            for backup in (conflicting, wrong_name, duplicate):
                with self.subTest(backup=backup), self.assertRaises(UserError):
                    RoleAuthorizationTransferService.import_backup(backup, apply=True)
        self.assertEqual(Role.objects.get(pk=self.role.pk).authorization, before)

    def test_existing_crud_expands_once_and_explicit_denial_wins(self):
        converted = RoleAuthorizationTransferService.convert_rows([('api.case:read', 'action'), (self.endpoint, Effect.DENY)])
        snapshot = converted['endpoint_permissions']
        http_id = http_endpoint_id('src.apps.auto_api.api.views.api_case.ApiCaseCRUD', 'get', 'get')
        self.assertEqual(snapshot[http_id], Effect.ALLOW)
        self.assertEqual(snapshot[self.endpoint], Effect.DENY)
        self.save(['api.case'], snapshot)
        self.assertEqual(Endpoint.for_role(self.role.id), snapshot)
        from django.apps import apps
        with self.assertRaises(LookupError):
            apps.get_model('user', 'RoleMenuPermission')

    def test_menu_visibility_does_not_grant_http_or_mcp_and_protocols_are_independent(self):
        http_id = http_endpoint_id('src.apps.auto_api.api.views.api_case.ApiCaseCRUD', 'get', 'get')
        self.save(['api.case'], {})
        user = SimpleNamespace(id=7, username='viewer', is_super_admin=False, role_id=self.role.id, role=self.role)
        self.assertNotIn('api.case:read', PermissionMenuService.permission_keys_for_user(user))
        self.assertFalse(Endpoint.allows(user, http_id, True))
        self.assertFalse(Endpoint.allows(user, self.endpoint, True))
        self.save(['api.case'], {http_id: Effect.ALLOW})
        self.assertTrue(Endpoint.allows(user, http_id, False))
        self.assertFalse(Endpoint.allows(user, self.endpoint, True))

    def test_repository_upsert_conversion_never_promotes_create_to_update(self):
        from src.apps.user.services.authorization.endpoint_catalog import http_request_endpoint_id
        owner = 'src.apps.auto_pytest.api.views.pytest_repository.PytestRepositoryViews'
        snapshot = Endpoint.from_legacy_keys({'pytest.repository:add'})
        for method in ('post', 'put'):
            create = http_request_endpoint_id(owner, 'save_repository', method, 'pytest.repository:add')
            update = http_request_endpoint_id(owner, 'save_repository', method, 'pytest.repository:change')
            self.assertNotEqual(create, update)
            self.assertEqual(snapshot[create], Effect.ALLOW)
            self.assertNotIn(update, snapshot)
            self.assertFalse(Endpoint.decision(snapshot, update, True))

    def setUp(self):
        self.alias = 'endpoint_permission_test'
        db = DatabaseWrapper({
            'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:', 'USER': '', 'PASSWORD': '',
            'HOST': '', 'PORT': '', 'OPTIONS': {}, 'TIME_ZONE': None, 'AUTOCOMMIT': True,
            'CONN_MAX_AGE': 0, 'CONN_HEALTH_CHECKS': False, 'ATOMIC_REQUESTS': False,
        }, alias=self.alias)
        db.ensure_connection()
        self.db = db
        connections[self.alias] = db
        def close():
            del connections[self.alias]
            db.connection.close()
        self.addCleanup(close)
        for model in (Role,):
            with db.cursor() as cursor:
                columns = ', '.join(f'"{field.column}" {field.db_type(db)}'
                                    + (' PRIMARY KEY' if field.primary_key else '') for field in model._meta.concrete_fields)
                cursor.execute(f'CREATE TABLE "{model._meta.db_table}" ({columns})')
            mocked = patch.object(model, 'objects', model.objects.using(self.alias))
            mocked.start()
            self.addCleanup(mocked.stop)
        self.role = Role.objects.create(name='普通角色')
        self.endpoint = mcp_endpoint_id('get_api_case_detail_full')

    def save(self, keys, overrides=None):
        with transaction.atomic(using=self.alias):
            return set(PermissionMenuService.save_role_permissions.__wrapped__(
                PermissionMenuService, self.role.id, keys, endpoint_permissions=overrides)['menu_keys'])

    def test_menu_and_endpoint_settings_save_together_and_crud_writes_are_rejected(self):
        keys = self.save(['api.case'], {self.endpoint: Effect.DENY})
        self.assertIn('api.case', keys)
        self.assertEqual(Endpoint.for_role(self.role.id), {self.endpoint: Effect.DENY})
        with self.assertRaises(UserError):
            self.save(['api.info:read'], {})
        with self.assertRaises(UserError):
            self.save(['__fixed__'], {})
        self.assertEqual(Endpoint.for_role(self.role.id), {self.endpoint: Effect.DENY})
        saved = Role.objects.get(pk=self.role.id).authorization
        self.assertEqual(set(saved), {'version', 'menu_keys', 'endpoint_permissions'})
        self.save([], {})
        self.assertEqual(Endpoint.for_role(self.role.id), {})

    def test_help_read_is_always_granted_even_for_existing_empty_roles(self):
        required = {'help', 'help.variable', 'help.variable:read', 'help.assertion',
                    'help.assertion:read', 'help.documents', 'help.documents:read'}
        user = SimpleNamespace(id=7, username='viewer', is_super_admin=False,
                               role_id=self.role.id, role=self.role)
        self.assertTrue(required <= PermissionMenuService.permission_keys_for_user(user))
        keys = self.save([], {})
        self.assertTrue({key for key in required if ':' not in key} <= keys)
        self.assertTrue(required <= PermissionMenuService.role_permission_keys(self.role.id))
        self.assertNotIn('help.variable:change', keys)
        self.assertNotIn('help.assertion:change', keys)
        endpoint = http_endpoint_id('src.apps.system.api.views.system_api.SystemViews', 'common_variable', 'get')
        self.assertNotIn(endpoint, configurable_endpoint_ids())
        self.assertNotIn(mcp_endpoint_id('list_test_data_methods'), configurable_endpoint_ids())
        with self.assertRaises(UserError):
            Endpoint.validate({endpoint: Effect.DENY})

    def test_invalid_snapshot_cannot_delete_existing_grants(self):
        self.save(['api.case'], {self.endpoint: Effect.ALLOW})
        with self.assertRaises(UserError):
            self.save([], {'invalid': Effect.ALLOW})
        self.assertIn('api.case:read', PermissionMenuService.role_permission_keys(self.role.id))
        self.assertEqual(Endpoint.for_role(self.role.id), {self.endpoint: Effect.ALLOW})

    def test_runtime_lookup_uses_role_and_endpoint_index_and_fixed_rules_do_not_query(self):
        self.save(['api.case'], {self.endpoint: Effect.ALLOW})
        user = SimpleNamespace(role_id=self.role.id, role=self.role)
        with CaptureQueriesContext(self.db) as queries:
            self.assertTrue(Endpoint.allows(user, self.endpoint, False))
        self.assertEqual(len(queries), 1)
        self.assertIn('authorization', queries[0]['sql'])
        self.assertNotIn('role_menu_permission', queries[0]['sql'])
        with CaptureQueriesContext(self.db) as queries:
            self.assertTrue(Endpoint.allows(user, mcp_endpoint_id('get_monitoring_script_context'), True))
        self.assertEqual(len(queries), 0)

    def test_guest_is_immutable_and_other_role_is_not_affected(self):
        guest = Role.objects.create(name='游客')
        with self.assertRaises(UserError):
            with transaction.atomic(using=self.alias):
                PermissionMenuService.save_role_permissions.__wrapped__(
                    PermissionMenuService, guest.id, [], endpoint_permissions={self.endpoint: Effect.ALLOW})
        self.save([], {self.endpoint: Effect.DENY})
        self.assertEqual(Endpoint.for_role(guest.id), {})
