from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from src.apps.auto_api.enums import ApiAuthRefreshModeEnum, ApiAuthTypeEnum
from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.services.api_auth_config import ApiAuthConfigService
from src.apps.auto_api.services.base.api_base_test_setup.auth_manager import ApiAuthManager
from src.apps.auto_api.api.serializers.api_auth_config_mutation import ApiAuthConfigSerializers
from src.apps.auto_api.api.views.api_auth_config import ApiAuthConfigViews, ApiAuthConfigCRUD
from src.apps.test_center.exceptions import TestCenterError
from src.common.testing import ObtainTestData
from src.interfaces.mcp.tools.api.auth_config import _write_payload


class AuthContextTests(SimpleTestCase):
    def config(self, ids=None, code=None):
        return SimpleNamespace(
            public_variable_ids=ids or [], project_product_id=1, test_env=0,
            auth_type=ApiAuthTypeEnum.CUSTOM.value, token_ttl=60, refresh_margin=10,
            refresh_mode=ApiAuthRefreshModeEnum.PASSIVE.value,
            custom_code=code or 'def auth(context):\n    return {"token": "example-token"}',
        )

    def setup_context(self, tenant=None):
        setup = MagicMock()
        setup.test_data = ObtainTestData()
        setup.test_object = SimpleNamespace(project_product_id=1, environment=0, value='', target_config={
            'selector': 'tenant_id', 'default': 'https://example.com',
            'mapping': {'new': 'https://example.org'},
        })
        initialized = []

        def init_public(product, env, ids=None):
            scope = (product, env, tuple(ids or []))
            if initialized and initialized[-1] == scope:
                return
            initialized.append(scope)
            setup.test_data.set_cache('tenant_id', 'new' if ids else 'default')

        setup.init_public.side_effect = init_public
        if tenant is not None:
            setup.test_data.set_cache('tenant_id', tenant)
        return setup

    def execute(self, manager, config, setup):
        rows = [SimpleNamespace(id=7, key='tenant_id', type=0, value='new', test_envs=[])] if config.public_variable_ids else []
        with patch('src.apps.auto_api.services.base.api_base_test_setup.APIBaseTestSetup', return_value=setup), \
                patch.object(ApiAuthConfigService, 'validate_public_variables', return_value=rows):
            return manager._refresh_in_isolated_context(config)

    def test_first_standalone_refresh_initializes_variables_before_fingerprinting(self):
        setup = self.setup_context()
        manager = ApiAuthManager()
        result = self.execute(manager, self.config([7]), setup)
        self.assertEqual(result['token'], 'example-token')
        self.assertEqual(result['__mango_auth_context__']['values'], {'tenant_id': 'new'})
        self.assertTrue(result['__mango_target_scope__'])
        self.assertIsNone(manager.test_setup)
        setup.close_db_connections.assert_called_once()

    def test_unbound_authorization_still_loads_defaults(self):
        setup = self.setup_context()
        result = self.execute(ApiAuthManager(), self.config(), setup)
        self.assertEqual(result['token'], 'example-token')
        self.assertNotIn('__mango_auth_context__', result)

    def test_matching_case_is_unchanged_by_authentication_initialization(self):
        caller = self.setup_context('new')
        before = dict(caller.test_data.get_all())
        manager = ApiAuthManager(caller)
        self.execute(manager, self.config([7]), self.setup_context())
        self.assertEqual(caller.test_data.get_all(), before)
        self.assertIs(manager.test_setup, caller)

    def test_mismatching_case_is_rejected_before_authentication(self):
        caller = self.setup_context('default')
        manager = ApiAuthManager(caller)
        with patch.object(manager, '_refresh_cache_data') as authenticate:
            with self.assertRaises(AutoApiError):
                self.execute(manager, self.config([7]), self.setup_context())
        authenticate.assert_not_called()
        self.assertEqual(caller.test_data.get_cache('tenant_id'), 'default')

    def test_real_condition_mutation_and_returned_condition_change_are_rejected(self):
        codes = [
            'def auth(context):\n    context.test_data.set_cache("tenant_id", "other")\n    return {"token": "example"}',
            'def auth(context):\n    return {"token": "example", "tenant_id": "other"}',
        ]
        for code in codes:
            with self.subTest(code=code), self.assertRaises(TestCenterError):
                self.execute(ApiAuthManager(), self.config([7], code), self.setup_context())

    def test_context_metadata_is_not_injected_and_cached_mismatch_is_rejected(self):
        caller = self.setup_context('default')
        config = self.config([7])
        config.cache_data = {'token': 'example', '__mango_target_scope__': 'scope',
                             '__mango_auth_context__': {'public_variable_ids': [7], 'values': {'tenant_id': 'new'},
                                'variables_checksum': ApiAuthConfigService.public_variables_checksum([])}}
        manager = ApiAuthManager(caller)
        with patch.object(ApiAuthConfigService, 'validate_public_variables', return_value=[]), self.assertRaises(AutoApiError):
            manager._is_cache_available(config)
        caller.test_data.set_cache('tenant_id', 'new')
        manager.inject_cache(config)
        self.assertNotIn('__mango_auth_context__', caller.test_data.get_all())
        self.assertEqual(caller.test_data.get_cache('tenant_id'), 'new')

    def test_changed_bound_variables_invalidate_cached_authentication(self):
        config = self.config([7])
        config.cache_data = {'token': 'example', '__mango_auth_context__': {
            'public_variable_ids': [7], 'values': {}, 'variables_checksum': 'old-checksum'}}
        with patch.object(ApiAuthConfigService, 'validate_public_variables', return_value=[]):
            self.assertFalse(ApiAuthManager()._is_cache_available(config))

    def test_binding_ids_validate_type_product_environment_and_duplicate_keys(self):
        for value in (None, '7', [True], [0], [-1]):
            with self.subTest(value=value), self.assertRaises(AutoApiError):
                ApiAuthConfigService.validate_public_variables(value, 1, 0)
        for rows in ([], [SimpleNamespace(key='tenant_id'), SimpleNamespace(key='tenant_id')]):
            with patch('src.apps.auto_api.services.api_auth_config.ApiPublic.objects.filter') as query:
                query.return_value.filter.return_value = rows
                with self.assertRaises(AutoApiError):
                    ApiAuthConfigService.validate_public_variables([7, 8], 1, 0)
                query.assert_called_once_with(id__in=[7, 8], project_product_id=1)

    def test_rest_and_mcp_preserve_binding_ids_and_allow_explicit_clear(self):
        with patch.object(ApiAuthConfigService, 'validate_public_variables') as validate:
            attrs = ApiAuthConfigSerializers().validate({'public_variable_ids': [7], 'project_product': SimpleNamespace(id=1),
                'test_env': 0, 'auth_type': ApiAuthTypeEnum.CUSTOM.value, 'custom_code': 'example', 'refresh_mode': 3})
            self.assertEqual(attrs['public_variable_ids'], [7])
            validate.assert_called_once_with([7], 1, 0)
        self.assertNotIn('public_variable_ids', _write_payload())
        self.assertEqual(_write_payload(public_variable_ids=[])['public_variable_ids'], [])
        self.assertEqual(_write_payload(include_none=True)['public_variable_ids'], [])

    def test_variable_options_require_scope_and_never_return_values(self):
        request = SimpleNamespace(query_params={'project_product': '1', 'test_env': '0'})
        with patch.object(ApiAuthConfigCRUD, 'has_data_scope_permission', return_value=False), \
                patch('src.apps.auto_api.api.views.api_auth_config.ApiQuerySelector.auth_public_variable_options') as query:
            response = ApiAuthConfigViews().public_variables(request)
            self.assertNotEqual(response.data['code'], 200)
            query.assert_not_called()
        with patch.object(ApiAuthConfigCRUD, 'has_data_scope_permission', return_value=True), \
                patch('src.apps.auto_api.api.views.api_auth_config.ApiQuerySelector.auth_public_variable_options') as query:
            query.return_value.count.return_value = 1
            query.return_value.values.return_value = [{'id': 7, 'key': 'tenant_id'}]
            response = ApiAuthConfigViews().public_variables(request)
            self.assertEqual(response.data['data'], [{'id': 7, 'key': 'tenant_id'}])
            self.assertNotIn('value', query.return_value.values.call_args.args)

    def test_mcp_create_and_update_forward_configured_variable_ids(self):
        from src.interfaces.mcp.tools.api.auth_config import register_api_auth_config_tools

        tools = {}
        class Capture:
            def tool(self):
                def register(function):
                    tools[function.__name__] = function
                    return function
                return register

        register_api_auth_config_tools(Capture())
        with patch.object(ApiAuthConfigService, 'create', return_value={'id': 1}) as create, \
                patch.object(ApiAuthConfigService, 'update', return_value={'id': 1}) as update, \
                patch('src.interfaces.mcp.tools.api.auth_config.mcp_current_user_id', return_value=9):
            tools['create_api_auth_config'](1, 0, 'Example', public_variable_ids=[7])
            self.assertEqual(create.call_args.args[0]['public_variable_ids'], [7])
            tools['update_api_auth_config'](1, public_variable_ids=[])
            self.assertEqual(update.call_args.args[1]['public_variable_ids'], [])
            tools['update_api_auth_config'](1, name='Renamed')
            self.assertNotIn('public_variable_ids', update.call_args.args[1])

    def test_options_endpoint_accepts_only_create_or_edit_permissions(self):
        from src.apps.user.middleware.permission import MenuActionPermission
        from src.apps.user.services.permission import PermissionMenuService

        view = ApiAuthConfigViews()
        view.action = 'public_variables'
        request = SimpleNamespace(method='GET', path='/api/api/auth/config/public-variables', data={},
                                  query_params={}, user=SimpleNamespace(user_obj=SimpleNamespace(id=9)))
        with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False):
            for key, expected in [('api.auth_config:add', True), ('api.auth_config:change', True),
                                  ('api.auth_config:read', False), ('api.auth_config', False)]:
                with patch.object(PermissionMenuService, 'permission_keys_for_user', return_value={key}):
                    self.assertEqual(MenuActionPermission().has_permission(request, view), expected)
